"""
ArXiv 논문 크롤러 with Review System
ArXiv에서 최신 논문을 가져와 리뷰를 생성하고 백엔드 API를 통해 데이터베이스에 저장하는 스크립트
"""

import asyncio
import io
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set

import arxiv
import PyPDF2
import requests
from dotenv import load_dotenv

from reviewer import Reviewer

# .env 파일에서 환경변수 로드
load_dotenv()

# API 설정
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/crawler/papers")
CRAWLER_SECRET_KEY = os.getenv("CRAWLER_SECRET_KEY")

if not CRAWLER_SECRET_KEY:
    raise ValueError("CRAWLER_SECRET_KEY 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요.")

# 처리된 논문 ID를 저장할 파일 경로
PROCESSED_PAPERS_FILE = "processed_papers.json"


def load_processed_papers() -> Set[str]:
    """처리된 논문 ID 목록을 로드"""
    if os.path.exists(PROCESSED_PAPERS_FILE):
        try:
            with open(PROCESSED_PAPERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("paper_ids", []))
        except (json.JSONDecodeError, FileNotFoundError):
            return set()
    return set()


def save_processed_paper(paper_id: str):
    """처리된 논문 ID를 저장"""
    processed = load_processed_papers()
    processed.add(paper_id)
    
    data = {
        "paper_ids": list(processed),
        "last_updated": datetime.now().isoformat()
    }
    
    with open(PROCESSED_PAPERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def extract_text_from_pdf(pdf_content: bytes) -> str:
    """
    PDF 바이너리 데이터에서 텍스트 추출
    
    Args:
        pdf_content: PDF 파일의 바이너리 데이터
    
    Returns:
        추출된 텍스트
    """
    try:
        pdf_file = io.BytesIO(pdf_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text_parts = []
        for page_num, page in enumerate(pdf_reader.pages):
            try:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            except Exception as e:
                print(f"페이지 {page_num + 1} 텍스트 추출 실패: {e}")
                continue
        
        full_text = "\n\n".join(text_parts)
        
        # 텍스트가 너무 길면 앞부분만 사용 (토큰 제한 고려)
        max_length = 100000  # 약 25,000 토큰 정도
        if len(full_text) > max_length:
            print(f"논문 텍스트가 너무 깁니다 ({len(full_text)} 문자). 앞부분 {max_length} 문자만 사용합니다.")
            full_text = full_text[:max_length]
        
        return full_text
    except Exception as e:
        print(f"PDF 텍스트 추출 실패: {e}")
        return ""


def fetch_latest_arxiv_papers(
    max_results: int = 50,
    sort_by: arxiv.SortCriterion = arxiv.SortCriterion.SubmittedDate,
    sort_order: arxiv.SortOrder = arxiv.SortOrder.Descending
) -> List[arxiv.Result]:
    """
    ArXiv에서 모든 분야의 최신 논문 가져오기
    
    Args:
        max_results: 가져올 최대 논문 수
        sort_by: 정렬 기준
        sort_order: 정렬 순서
    
    Returns:
        ArXiv Result 객체 리스트
    """
    # 모든 분야를 포함하는 쿼리 (빈 쿼리는 모든 논문을 의미)
    query = ""
    
    print(f"ArXiv에서 최신 논문 검색 중... (최대 {max_results}개)")
    
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    client = arxiv.Client()
    results = list(client.results(search))
    
    print(f"논문 {len(results)}개 발견")
    return results


def download_pdf(pdf_url: str) -> Optional[bytes]:
    """
    PDF 파일을 다운로드하는 함수
    
    Args:
        pdf_url: PDF 파일의 URL
    
    Returns:
        PDF 파일의 바이너리 데이터 또는 None
    """
    try:
        response = requests.get(pdf_url, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"PDF 다운로드 실패: {str(e)[:50]}")
        return None


def transform_arxiv_to_api_format(arxiv_result: arxiv.Result) -> Dict:
    """
    ArXiv 결과를 API 형식으로 변환
    
    Args:
        arxiv_result: ArXiv Result 객체
    
    Returns:
        API 형식의 딕셔너리
    """
    # 논문 ID 추출 (entry_id에서 마지막 부분만 추출)
    paper_id = arxiv_result.entry_id.split('/')[-1] if arxiv_result.entry_id else None
    
    if not paper_id:
        raise ValueError("논문 ID를 추출할 수 없습니다.")
    
    # DOI 추출
    doi = None
    try:
        if hasattr(arxiv_result, 'doi') and arxiv_result.doi:
            doi = str(arxiv_result.doi)
    except:
        pass
    
    if not doi:
        doi = f"arXiv:{paper_id}"
    else:
        if not doi.startswith("http"):
            doi = f"https://doi.org/{doi}"
    
    # 카테고리 처리
    category_codes = list(arxiv_result.categories) if arxiv_result.categories else []
    categories = category_codes  # 카테고리 코드 그대로 사용
    
    # 저자 목록
    authors = [author.name for author in arxiv_result.authors] if arxiv_result.authors else []
    
    # 발행일 ISO 8601 형식으로 변환
    issued_at = None
    if arxiv_result.published:
        issued_at = arxiv_result.published.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # PDF URL 구성
    pdf_url = None
    if arxiv_result.entry_id:
        pdf_url = arxiv_result.entry_id.replace('/abs/', '/pdf/') + '.pdf'
    
    # API 형식으로 변환
    paper_data = {
        "paperId": paper_id,
        "title": arxiv_result.title or "",
        "categories": json.dumps(categories),
        "authors": json.dumps(authors),
        "summary": arxiv_result.summary or "",
        "doi": doi,
        "url": arxiv_result.entry_id or "",
        "pdfUrl": pdf_url or "",
        "issuedAt": issued_at or ""
    }
    
    return paper_data


async def generate_review_for_paper(paper_content: str) -> Optional[Dict]:
    """
    논문에 대한 리뷰 생성
    
    Args:
        paper_content: 논문 텍스트 내용
    
    Returns:
        리뷰 딕셔너리 또는 None
    """
    try:
        reviewer = Reviewer(model="gpt-4o-mini")
        reviews = await reviewer.review(paper_content, reflection=3)
        
        if reviews:
            # 앙상블 리뷰 생성
            final_reviews = await reviewer.review_ensembling()
            if final_reviews:
                return final_reviews[0]
        
        return None
    except Exception as e:
        print(f"리뷰 생성 실패: {e}")
        return None


def upload_paper_with_review(paper_data: Dict, review: Optional[Dict] = None) -> bool:
    """
    API를 통해 논문과 리뷰 업로드
    
    Args:
        paper_data: 논문 데이터 딕셔너리
        review: 리뷰 딕셔너리 (선택사항)
    
    Returns:
        성공 여부 (bool)
    """
    title_display = paper_data['title'][:50] + "..." if len(paper_data['title']) > 50 else paper_data['title']
    print(f"업로드 중: \"{title_display}\"", end=" ... ", flush=True)
    
    try:
        headers = {
            "Authorization": f"Bearer {CRAWLER_SECRET_KEY}"
        }
        
        # PDF 파일 다운로드
        pdf_content = None
        files = {}
        
        if 'pdfUrl' in paper_data and paper_data['pdfUrl']:
            pdf_content = download_pdf(paper_data['pdfUrl'])
            if pdf_content:
                paper_id = paper_data.get('paperId', 'paper_unknown')
                files['pdf'] = (f'{paper_id}.pdf', pdf_content, 'application/pdf')
        
        if not pdf_content:
            print("실패 (PDF 다운로드 불가)")
            return False
        
        # 데이터 준비
        data = {}
        
        # 모든 필드를 data에 추가 (pdfUrl은 제외)
        for key, value in paper_data.items():
            if key == 'pdfUrl':
                continue
            if value is not None and value != "":
                if isinstance(value, (list, dict)):
                    data[key] = json.dumps(value)
                else:
                    data[key] = str(value)
        
        # 리뷰가 있으면 content 필드에 추가
        if review:
            content_data = {
                "review": review
            }
            data['content'] = json.dumps(content_data)
        else:
            # 리뷰가 없으면 빈 객체
            data['content'] = json.dumps({})
        
        response = requests.post(
            API_BASE_URL,
            headers=headers,
            data=data,
            files=files,
            timeout=120  # 리뷰 생성 시간을 고려하여 타임아웃 증가
        )
        
        if response.status_code == 200 or response.status_code == 201:
            print("성공")
            return True
        else:
            print(f"실패 (HTTP {response.status_code}: {response.text[:100]})")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"실패 (네트워크 오류: {str(e)[:50]})")
        return False
    except Exception as e:
        print(f"실패 (오류: {str(e)[:50]})")
        return False


async def process_new_papers():
    """새로운 논문을 처리하는 메인 함수"""
    print("=" * 60)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 논문 크롤링 시작...")
    print("=" * 60)
    
    try:
        # 처리된 논문 ID 로드
        processed_papers = load_processed_papers()
        print(f"이미 처리된 논문: {len(processed_papers)}개")
        
        # 최신 논문 가져오기
        papers = fetch_latest_arxiv_papers(max_results=50)
        
        if not papers:
            print("가져올 논문이 없습니다.")
            return
        
        # 새로운 논문만 필터링
        new_papers = []
        for paper in papers:
            paper_id = paper.entry_id.split('/')[-1] if paper.entry_id else None
            if paper_id and paper_id not in processed_papers:
                new_papers.append(paper)
        
        if not new_papers:
            print(f"새로운 논문이 없습니다. (전체 {len(papers)}개 중 모두 처리됨)")
            return
        
        print(f"\n새로운 논문 {len(new_papers)}개 발견\n")
        
        # 각 논문 처리
        success_count = 0
        fail_count = 0
        
        for index, paper in enumerate(new_papers, start=1):
            paper_id = paper.entry_id.split('/')[-1] if paper.entry_id else None
            
            try:
                # ArXiv 결과를 API 형식으로 변환
                paper_data = transform_arxiv_to_api_format(paper)
                
                # PDF 다운로드 및 텍스트 추출
                pdf_url = paper_data.get('pdfUrl')
                paper_content = ""
                
                if pdf_url:
                    pdf_content = download_pdf(pdf_url)
                    if pdf_content:
                        paper_content = extract_text_from_pdf(pdf_content)
                
                # 리뷰 생성
                review = None
                if paper_content:
                    print(f"[{index}/{len(new_papers)}] 리뷰 생성 중: {paper_data['title'][:50]}...")
                    review = await generate_review_for_paper(paper_content)
                
                # API를 통해 업로드
                if upload_paper_with_review(paper_data, review):
                    success_count += 1
                    save_processed_paper(paper_id)
                else:
                    fail_count += 1
                
                # Rate limiting: 요청 간 딜레이 추가
                if index < len(new_papers):
                    await asyncio.sleep(2)  # 2초 딜레이
                    
            except Exception as e:
                print(f"[{index}/{len(new_papers)}] 처리 실패: {str(e)[:100]}")
                fail_count += 1
                continue
        
        # 결과 통계 출력
        print("\n" + "=" * 60)
        print("크롤링 완료!")
        print("=" * 60)
        print(f"성공: {success_count}개")
        print(f"실패: {fail_count}개")
        print(f"전체: {len(new_papers)}개")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n치명적 오류 발생: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """메인 함수 - 1분마다 실행"""
    print("ArXiv 크롤러 시작 (1분마다 실행)")
    print("종료하려면 Ctrl+C를 누르세요.")
    
    while True:
        try:
            await process_new_papers()
            print(f"\n다음 크롤링까지 60초 대기...")
            await asyncio.sleep(60)  # 1분 대기
        except KeyboardInterrupt:
            print("\n\n크롤러 종료")
            break
        except Exception as e:
            print(f"\n오류 발생: {e}")
            print("60초 후 재시도...")
            await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())

