"""
ArXiv 논문 크롤러
ArXiv에서 논문을 가져와 백엔드 API를 통해 데이터베이스에 저장하는 스크립트
"""

import asyncio
import base64
import io
import json
import os
import sys
import time
from typing import Dict, List, Optional

import arxiv
import PyPDF2
import requests
from dotenv import load_dotenv

from reviewer import Reviewer

# .env 파일에서 환경변수 로드
load_dotenv()

# API 설정
BACKEND_SERVER_URL = os.getenv("BACKEND_SERVER_URL", "http://localhost:8000")
AI_SERVER_URL = os.getenv("AI_SERVER_URL", "https://med-role-alternatives-sol.trycloudflare.com")
CRAWLER_SECRET_KEY = os.getenv("CRAWLER_SECRET_KEY")

# URL 구성
ACTIVITIES_URL = f"{BACKEND_SERVER_URL}/api/crawler/users/activities"
PAPERS_CREATE_URL = f"{BACKEND_SERVER_URL}/api/crawler/papers"
AI_SUMMARIZE_URL = f"{AI_SERVER_URL}/api/summarize-paper"

if not CRAWLER_SECRET_KEY:
    raise ValueError("CRAWLER_SECRET_KEY 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요.")


def fetch_arxiv_papers(
    query: str = "cat:cs.AI OR cat:cs.LG OR cat:cs.CV",
    max_results: int = 100,
    sort_by: arxiv.SortCriterion = arxiv.SortCriterion.SubmittedDate,
    sort_order: arxiv.SortOrder = arxiv.SortOrder.Descending
) -> List[arxiv.Result]:
    """
    ArXiv에서 논문 목록 가져오기
    
    Args:
        query: 검색 쿼리
        max_results: 가져올 최대 논문 수
        sort_by: 정렬 기준
        sort_order: 정렬 순서
    
    Returns:
        ArXiv Result 객체 리스트
    """
    print(f"ArXiv에서 논문 검색 중... (쿼리: {query})")
    
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


# ArXiv 카테고리 코드를 사람이 읽을 수 있는 이름으로 매핑
ARXIV_CATEGORY_MAPPING = {
    # Computer Science
    "cs.AI": "Artificial Intelligence",
    "cs.CL": "Computation and Language",
    "cs.CC": "Computational Complexity",
    "cs.CE": "Computational Engineering, Finance, and Science",
    "cs.CG": "Computational Geometry",
    "cs.GT": "Computer Science and Game Theory",
    "cs.CV": "Computer Vision and Pattern Recognition",
    "cs.CY": "Computers and Society",
    "cs.CR": "Cryptography and Security",
    "cs.DS": "Data Structures and Algorithms",
    "cs.DB": "Databases",
    "cs.DL": "Digital Libraries",
    "cs.DM": "Discrete Mathematics",
    "cs.DC": "Distributed, Parallel, and Cluster Computing",
    "cs.GL": "General Literature",
    "cs.GR": "Graphics",
    "cs.AR": "Hardware Architecture",
    "cs.HC": "Human-Computer Interaction",
    "cs.IR": "Information Retrieval",
    "cs.IT": "Information Theory",
    "cs.LG": "Machine Learning",
    "cs.LO": "Logic in Computer Science",
    "cs.MS": "Mathematical Software",
    "cs.MA": "Multiagent Systems",
    "cs.MM": "Multimedia",
    "cs.NI": "Networking and Internet Architecture",
    "cs.NE": "Neural and Evolutionary Computing",
    "cs.NA": "Numerical Analysis",
    "cs.OS": "Operating Systems",
    "cs.OH": "Other Computer Science",
    "cs.PF": "Performance",
    "cs.PL": "Programming Languages",
    "cs.RO": "Robotics",
    "cs.SI": "Social and Information Networks",
    "cs.SE": "Software Engineering",
    "cs.SD": "Sound",
    "cs.SC": "Symbolic Computation",
    "cs.SY": "Systems and Control",
    # Mathematics
    "math.AG": "Algebraic Geometry",
    "math.AT": "Algebraic Topology",
    "math.AP": "Analysis of PDEs",
    "math.CT": "Category Theory",
    "math.CA": "Classical Analysis and ODEs",
    "math.CO": "Combinatorics",
    "math.AC": "Commutative Algebra",
    "math.CV": "Complex Variables",
    "math.DG": "Differential Geometry",
    "math.DS": "Dynamical Systems",
    "math.FA": "Functional Analysis",
    "math.GM": "General Mathematics",
    "math.GN": "General Topology",
    "math.GT": "Geometric Topology",
    "math.GR": "Group Theory",
    "math.HO": "History and Overview",
    "math.IT": "Information Theory",
    "math.KT": "K-Theory and Homology",
    "math.LO": "Logic",
    "math.MP": "Mathematical Physics",
    "math.MG": "Metric Geometry",
    "math.NT": "Number Theory",
    "math.NA": "Numerical Analysis",
    "math.OA": "Operator Algebras",
    "math.OC": "Optimization and Control",
    "math.PR": "Probability",
    "math.QA": "Quantum Algebra",
    "math.RT": "Representation Theory",
    "math.RA": "Rings and Algebras",
    "math.SP": "Spectral Theory",
    "math.ST": "Statistics Theory",
    "math.SG": "Symplectic Geometry",
    # Physics
    "physics.acc-ph": "Accelerator Physics",
    "physics.app-ph": "Applied Physics",
    "physics.ao-ph": "Atmospheric and Oceanic Physics",
    "physics.atom-ph": "Atomic Physics",
    "physics.atm-clus": "Atomic and Molecular Clusters",
    "physics.bio-ph": "Biological Physics",
    "physics.chem-ph": "Chemical Physics",
    "physics.class-ph": "Classical Physics",
    "physics.comp-ph": "Computational Physics",
    "physics.data-an": "Data Analysis, Statistics and Probability",
    "physics.flu-dyn": "Fluid Dynamics",
    "physics.gen-ph": "General Physics",
    "physics.geo-ph": "Geophysics",
    "physics.hist-ph": "History and Philosophy of Physics",
    "physics.ins-det": "Instrumentation and Detectors",
    "physics.med-ph": "Medical Physics",
    "physics.optics": "Optics",
    "physics.ed-ph": "Physics Education",
    "physics.soc-ph": "Physics and Society",
    "physics.plasm-ph": "Plasma Physics",
    "physics.pop-ph": "Popular Physics",
    "physics.space-ph": "Space Physics",
    # Astrophysics
    "astro-ph.GA": "Galaxy Astrophysics",
    "astro-ph.CO": "Cosmology and Nongalactic Astrophysics",
    "astro-ph.EP": "Earth and Planetary Astrophysics",
    "astro-ph.HE": "High Energy Astrophysical Phenomena",
    "astro-ph.IM": "Instrumentation and Methods for Astrophysics",
    "astro-ph.SR": "Solar and Stellar Astrophysics",
    # Quantitative Biology
    "q-bio.BM": "Biomolecules",
    "q-bio.CB": "Cell Behavior",
    "q-bio.GN": "Genomics",
    "q-bio.MN": "Molecular Networks",
    "q-bio.NC": "Neurons and Cognition",
    "q-bio.OT": "Other Quantitative Biology",
    "q-bio.PE": "Populations and Evolution",
    "q-bio.QM": "Quantitative Methods",
    "q-bio.SC": "Subcellular Processes",
    "q-bio.TO": "Tissues and Organs",
    # Quantitative Finance
    "q-fin.CP": "Computational Finance",
    "q-fin.EC": "Economics",
    "q-fin.GN": "General Finance",
    "q-fin.MF": "Mathematical Finance",
    "q-fin.PM": "Portfolio Management",
    "q-fin.PR": "Pricing of Securities",
    "q-fin.RM": "Risk Management",
    "q-fin.ST": "Statistical Finance",
    "q-fin.TR": "Trading and Market Microstructure",
    # Statistics
    "stat.AP": "Applications",
    "stat.CO": "Computation",
    "stat.ML": "Machine Learning",
    "stat.ME": "Methodology",
    "stat.OT": "Other Statistics",
    "stat.TH": "Statistics Theory",
    # Electrical Engineering and Systems Science
    "eess.AS": "Audio and Speech Processing",
    "eess.IV": "Image and Video Processing",
    "eess.SP": "Signal Processing",
    "eess.SY": "Systems and Control",
}


def map_category_code_to_name(category_code: str) -> str:
    """
    ArXiv 카테고리 코드를 사람이 읽을 수 있는 이름으로 변환
    
    Args:
        category_code: ArXiv 카테고리 코드 (예: "cs.AI", "cs.CV")
    
    Returns:
        사람이 읽을 수 있는 카테고리 이름 (예: "Artificial Intelligence", "Computer Vision and Pattern Recognition")
    """
    return ARXIV_CATEGORY_MAPPING.get(category_code, category_code)


def extract_doi_from_result(paper: arxiv.Result) -> Optional[str]:
    """
    Result 객체에서 DOI를 추출하는 함수
    
    Args:
        paper: arxiv Result 객체
    
    Returns:
        DOI 문자열 또는 None
    """
    # 방법 1: Result 객체의 doi 속성 직접 확인
    try:
        if hasattr(paper, 'doi') and paper.doi:
            return str(paper.doi)
    except (AttributeError, TypeError):
        pass
    
    # 방법 2: feedparser의 entry 객체에서 arxiv_doi 확인
    try:
        if hasattr(paper, '_raw'):
            entry = paper._raw
            if hasattr(entry, 'arxiv_doi') and entry.arxiv_doi:
                return str(entry.arxiv_doi)
        
        if hasattr(paper, 'arxiv_doi') and paper.arxiv_doi:
            return str(paper.arxiv_doi)
        
        if hasattr(paper, '__dict__'):
            paper_dict = paper.__dict__
            if '_raw' in paper_dict:
                raw_entry = paper_dict['_raw']
                if hasattr(raw_entry, 'arxiv_doi') and raw_entry.arxiv_doi:
                    return str(raw_entry.arxiv_doi)
            
            if 'arxiv_doi' in paper_dict and paper_dict['arxiv_doi']:
                return str(paper_dict['arxiv_doi'])
    except Exception:
        pass
    
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
    doi = extract_doi_from_result(arxiv_result)
    if not doi:
        # DOI가 없으면 arXiv:{paper_id} 형식 사용
        doi = f"arXiv:{paper_id}"
    else:
        # DOI가 있으면 링크 형식으로 변환
        # 이미 https://doi.org/로 시작하는 경우 그대로 사용
        if not doi.startswith("http"):
            doi = f"https://doi.org/{doi}"
    
    # 카테고리 처리 - 코드를 사람이 읽을 수 있는 이름으로 변환
    category_codes = list(arxiv_result.categories) if arxiv_result.categories else []
    categories = [map_category_code_to_name(code) for code in category_codes]
    
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
    # translatedSummary, content, hashtags 등은 AI 서버 응답에서 가져옴
    paper_data = {
        "paperId": paper_id,
        "title": arxiv_result.title or "",
        "categories": json.dumps(categories),  # 배열을 JSON 문자열로 변환
        "authors": json.dumps(authors),  # 배열을 JSON 문자열로 변환
        "summary": arxiv_result.summary or "",
        "doi": doi,
        "url": arxiv_result.entry_id or "",
        "pdfUrl": pdf_url or "",
        "issuedAt": issued_at or ""
    }
    
    return paper_data


def fetch_user_activities() -> Optional[List[Dict]]:
    """
    백엔드 서버에서 사용자 활동 정보 가져오기
    
    Returns:
        사용자 활동 목록 또는 None
    """
    try:
        headers = {
            "Authorization": f"Bearer {CRAWLER_SECRET_KEY}"
        }
        response = requests.get(ACTIVITIES_URL, headers=headers, timeout=30)
        response.raise_for_status()
        activities = response.json()
        print(f"사용자 활동 {len(activities) if isinstance(activities, list) else 1}개 가져오기 성공")
        return activities
    except requests.exceptions.RequestException as e:
        print(f"경고: 사용자 활동 가져오기 실패: {str(e)[:100]}")
        return None
    except Exception as e:
        print(f"경고: 사용자 활동 처리 중 오류: {str(e)[:100]}")
        return None


def load_thumbnail() -> Optional[bytes]:
    """
    thumbnail.webp 파일을 로드하는 함수
    
    Returns:
        thumbnail.webp 파일의 바이너리 데이터 또는 None
    """
    try:
        thumbnail_path = os.path.join(os.path.dirname(__file__), "thumbnail.webp")
        with open(thumbnail_path, "rb") as f:
            return f.read()
    except FileNotFoundError:
        print("경고: thumbnail.webp 파일을 찾을 수 없습니다.")
        return None


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


def extract_text_from_pdf(pdf_content: bytes) -> str:
    """
    PDF 파일에서 텍스트를 추출하는 함수
    
    Args:
        pdf_content: PDF 파일의 바이너리 데이터
    
    Returns:
        추출된 텍스트 또는 빈 문자열
    """
    try:
        pdf_file = io.BytesIO(pdf_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        
        # 텍스트가 너무 길면 앞부분만 사용 (토큰 제한 고려)
        if len(text) > 100000:
            text = text[:100000]
        
        return text
    except Exception as e:
        print(f"    ⚠ 경고: PDF 텍스트 추출 실패: {str(e)[:50]}")
        return ""


async def review_paper(pdf_content: bytes, reviewer: Reviewer) -> Optional[Dict]:
    """
    Reviewer를 사용하여 논문이 적절한지 판단
    
    Args:
        pdf_content: PDF 파일의 바이너리 데이터
        reviewer: Reviewer 인스턴스
    
    Returns:
        리뷰 결과 (적절한 논문이면 리뷰 데이터, 아니면 None)
    """
    try:
        # PDF에서 텍스트 추출
        paper_text = extract_text_from_pdf(pdf_content)
        
        if not paper_text:
            print("    ⚠ 텍스트 추출 실패, 리뷰 건너뜀")
            return None
        
        # Reviewer로 논문 리뷰
        print("  → Reviewer로 논문 적절성 판단 중...", end=" ", flush=True)
        reviews = await reviewer.review(paper_text, reflection=1)  # reflection 1회로 빠르게 판단
        
        if not reviews or len(reviews) == 0:
            print("실패 (리뷰 없음)")
            return None
        
        # 첫 번째 리뷰 결과 확인
        review_result = reviews[0]
        
        # 논문이 적절한지 판단 (예: rating이 5 이상이면 적절하다고 판단)
        # 실제 판단 로직은 프로젝트 요구사항에 맞게 조정 필요
        is_appropriate = True  # 기본적으로 모든 논문을 적절하다고 판단
        
        if 'rating' in review_result:
            rating = review_result.get('rating', 0)
            is_appropriate = rating >= 5
        
        if is_appropriate:
            print("성공 (적절한 논문)")
            return review_result
        else:
            print(f"부적절 (rating: {review_result.get('rating', 'N/A')})")
            return None
            
    except Exception as e:
        print(f"실패 (오류: {str(e)[:100]})")
        return None


def process_ai_response(ai_response: Dict) -> Dict:
    """
    AI 서버 응답을 백엔드에 전송할 형식으로 처리
    
    Args:
        ai_response: AI 서버 응답
    
    Returns:
        처리된 데이터 딕셔너리
    """
    processed = {}
    
    # 1. summary와 translatedSummary 추가
    if 'summary' in ai_response:
        processed['summary'] = ai_response['summary']
    if 'translatedSummary' in ai_response:
        processed['translatedSummary'] = ai_response['translatedSummary']
    
    # 2. tableOfContents와 contents를 content 필드로 통합
    content_data = {}
    if 'tableOfContents' in ai_response:
        content_data['tableOfContents'] = ai_response['tableOfContents']
    if 'contents' in ai_response:
        content_data['contents'] = ai_response['contents']
    
    if content_data:
        processed['content'] = json.dumps(content_data, ensure_ascii=False)
    
    # 3. hashtags 추가
    if 'hashtags' in ai_response:
        processed['hashtags'] = json.dumps(ai_response['hashtags'], ensure_ascii=False)
    
    # 4. interestedUsers에서 userId만 추출하여 배열로 변환
    if 'interestedUsers' in ai_response and isinstance(ai_response['interestedUsers'], list):
        interested_user_ids = [user['userId'] for user in ai_response['interestedUsers'] if 'userId' in user]
        processed['interestedUsers'] = json.dumps(interested_user_ids, ensure_ascii=False)
    
    # 5. thumbnail은 base64이므로 별도 처리 (bytes로 변환)
    if 'thumbnail' in ai_response and ai_response['thumbnail']:
        try:
            # base64 디코드
            thumbnail_bytes = base64.b64decode(ai_response['thumbnail'])
            processed['thumbnail_bytes'] = thumbnail_bytes
        except Exception as e:
            print(f"    ⚠ 경고: 썸네일 디코딩 실패: {str(e)[:50]}")
    
    return processed


def summarize_paper_with_ai(pdf_content: bytes, activities: List[Dict], paper_id: str) -> Optional[Dict]:
    """
    AI 서버로 PDF와 활동 정보를 전송하여 논문 요약 받기
    
    Args:
        pdf_content: PDF 파일의 바이너리 데이터
        activities: 사용자 활동 정보 목록
        paper_id: 논문 ID
    
    Returns:
        처리된 AI 서버 응답 (딕셔너리) 또는 None
    """
    try:
        # multipart/form-data로 전송
        files = {
            'file': (f'{paper_id}.pdf', pdf_content, 'application/pdf')
        }
        
        data = {
            'activity': json.dumps(activities)
        }
        
        print("  → AI 서버로 요약 요청 중...", end=" ", flush=True)
        response = requests.post(
            AI_SUMMARIZE_URL,
            files=files,
            data=data,
            timeout=120  # AI 처리 시간을 고려하여 타임아웃 증가
        )
        response.raise_for_status()
        
        ai_response = response.json()
        print("성공")
        
        # AI 응답 처리
        processed_response = process_ai_response(ai_response)
        
        # 응답 요약 출력 (전체 응답은 너무 길어서 주요 필드만 출력)
        summary_info = {
            'has_summary': 'summary' in processed_response,
            'has_translatedSummary': 'translatedSummary' in processed_response,
            'has_content': 'content' in processed_response,
            'has_hashtags': 'hashtags' in processed_response,
            'has_thumbnail': 'thumbnail_bytes' in processed_response,
            'interested_users_count': len(json.loads(processed_response.get('interestedUsers', '[]')))
        }
        print(f"  → AI 응답 처리 완료: {json.dumps(summary_info, ensure_ascii=False)}")
        
        return processed_response
        
    except requests.exceptions.RequestException as e:
        print(f"실패 (네트워크 오류: {str(e)[:100]})")
        return None
    except json.JSONDecodeError as e:
        print(f"실패 (응답 파싱 오류: {str(e)[:100]})")
        return None
    except Exception as e:
        print(f"실패 (오류: {str(e)[:100]})")
        return None


async def upload_paper(paper_data: Dict, activities: Optional[List[Dict]], reviewer: Reviewer, index: int, total: int) -> bool:
    """
    AI 서버로 논문 요약 후 백엔드 API를 통해 논문 업로드
    
    Args:
        paper_data: 논문 데이터 딕셔너리
        activities: 사용자 활동 정보 목록
        index: 현재 인덱스 (1부터 시작)
        total: 전체 개수
    
    Returns:
        성공 여부 (bool)
    """
    title_display = paper_data['title'][:50] + "..." if len(paper_data['title']) > 50 else paper_data['title']
    print(f"[{index}/{total}] 처리 중: \"{title_display}\"")
    
    try:
        headers = {
            "Authorization": f"Bearer {CRAWLER_SECRET_KEY}"
        }
        
        # PDF 파일 다운로드
        pdf_content = None
        files = {}
        
        if 'pdfUrl' in paper_data and paper_data['pdfUrl']:
            print("  → PDF 다운로드 중...", end=" ", flush=True)
            pdf_content = download_pdf(paper_data['pdfUrl'])
            if pdf_content:
                print("성공")
                paper_id = paper_data.get('paperId', f'paper_{index}')
                files['pdf'] = (f'{paper_id}.pdf', pdf_content, 'application/pdf')
            else:
                print("실패")
        
        if not pdf_content:
            print("  ✗ 실패 (PDF 다운로드 불가)")
            return False
        
        # 1단계: Reviewer로 논문 적절성 판단
        review_result = None
        if reviewer:
            review_result = await review_paper(pdf_content, reviewer)
            
            if not review_result:
                print("  ✗ 부적절한 논문, 건너뜀\n")
                return False
        else:
            print("  → Reviewer 없음, 모든 논문 적절하다고 판단")
        
        # 2단계: AI 서버로 논문 요약 요청 (적절한 논문만)
        ai_response = None
        if activities:
            ai_response = summarize_paper_with_ai(
                pdf_content, 
                activities, 
                paper_data.get('paperId', f'paper_{index}')
            )
        else:
            print("  ⚠ 경고: 사용자 활동 정보 없음, AI 요약 건너뜀")
        
        # multipart/form-data 형식으로 데이터 전송
        data = {}
        
        # 기본 논문 데이터 추가 (pdfUrl은 제외, pdf 파일로 대체)
        for key, value in paper_data.items():
            if key in ['pdfUrl', 'translatedSummary']:  # pdfUrl과 translatedSummary는 제외 (AI 응답에서 가져옴)
                continue
            if value is not None and value != "":
                # 문자열로 변환 (이미 JSON 문자열인 경우 그대로 사용)
                if isinstance(value, (list, dict)):
                    data[key] = json.dumps(value)
                else:
                    data[key] = str(value)
        
        # AI 응답이 있으면 데이터에 추가
        if ai_response:
            # summary와 translatedSummary (AI 응답 우선)
            if 'summary' in ai_response:
                data['summary'] = ai_response['summary']
            if 'translatedSummary' in ai_response:
                data['translatedSummary'] = ai_response['translatedSummary']
            
            # content (tableOfContents + contents)
            if 'content' in ai_response:
                data['content'] = ai_response['content']
            
            # hashtags
            if 'hashtags' in ai_response:
                data['hashtags'] = ai_response['hashtags']
            
            # interestedUsers (userId 배열)
            if 'interestedUsers' in ai_response:
                data['interestedUsers'] = ai_response['interestedUsers']
            
            # thumbnail (base64 -> bytes)
            if 'thumbnail_bytes' in ai_response:
                files['thumbnail'] = ('thumbnail.png', ai_response['thumbnail_bytes'], 'image/png')
        
        # AI 응답이 없으면 기본 썸네일 사용
        if 'thumbnail' not in files:
            thumbnail_content = load_thumbnail()
            if thumbnail_content:
                files['thumbnail'] = ('thumbnail.webp', thumbnail_content, 'image/webp')
        
        print("  → 백엔드 서버로 업로드 중...", end=" ", flush=True)
        response = requests.post(
            PAPERS_CREATE_URL,
            headers=headers,
            data=data,
            files=files,
            timeout=60  # PDF 업로드 시간을 고려하여 타임아웃 증가
        )
        
        if response.status_code == 200 or response.status_code == 201:
            print("성공")
            print("  ✓ 완료\n")
            return True
        else:
            print(f"실패 (HTTP {response.status_code}: {response.text[:100]})")
            print("  ✗ 실패\n")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"실패 (네트워크 오류: {str(e)[:50]})")
        print("  ✗ 실패\n")
        return False
    except Exception as e:
        print(f"실패 (오류: {str(e)[:50]})")
        print("  ✗ 실패\n")
        return False


def fetch_latest_papers(max_results: int = 100) -> List[arxiv.Result]:
    """
    최신 논문 100개 가져오기
    
    Args:
        max_results: 가져올 최대 논문 수
    
    Returns:
        ArXiv Result 객체 리스트
    """
    return fetch_arxiv_papers(
        query="cat:cs.AI OR cat:cs.LG OR cat:cs.CV",
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending
    )


def fetch_scheduled_papers(query: str = "cat:cs.AI OR cat:cs.LG OR cat:cs.CV", 
                          max_results: int = 10) -> List[arxiv.Result]:
    """
    스케줄링용 논문 가져오기 (최신 10개 정도)
    
    Args:
        query: 검색 쿼리
        max_results: 가져올 최대 논문 수
    
    Returns:
        ArXiv Result 객체 리스트
    """
    return fetch_arxiv_papers(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending
    )


async def process_papers(papers: List[arxiv.Result], mode: str = "latest") -> Dict[str, int]:
    """
    논문 목록을 처리하는 공통 함수
    
    Args:
        papers: ArXiv Result 객체 리스트
        mode: 처리 모드 ("latest" 또는 "scheduled")
    
    Returns:
        처리 결과 통계 (성공, 실패, 전체 개수)
    """
    if not papers:
        print("가져올 논문이 없습니다.")
        return {"success": 0, "fail": 0, "total": 0}
    
    print(f"\n논문 {len(papers)}개 발견\n")
    
    # 0. Reviewer 초기화
    print("Reviewer 초기화 중...")
    try:
        reviewer = Reviewer()
        print("Reviewer 초기화 완료\n")
    except Exception as e:
        print(f"⚠ 경고: Reviewer 초기화 실패: {str(e)[:100]}")
        print("Reviewer 없이 진행합니다 (모든 논문을 적절하다고 판단).\n")
        reviewer = None
    
    # 1. 사용자 활동 정보 가져오기
    print("사용자 활동 정보 가져오는 중...")
    activities = fetch_user_activities()
    
    if not activities:
        print("⚠ 경고: 사용자 활동 정보를 가져오지 못했습니다. AI 요약 없이 진행합니다.\n")
    else:
        print()
    
    # 2. 각 논문을 API 형식으로 변환하고 업로드
    success_count = 0
    fail_count = 0
    
    for index, paper in enumerate(papers, start=1):
        try:
            # ArXiv 결과를 API 형식으로 변환
            paper_data = transform_arxiv_to_api_format(paper)
            
            # API를 통해 업로드 (Reviewer + AI 요약 포함)
            result = await upload_paper(paper_data, activities, reviewer, index, len(papers))
            
            if result:
                success_count += 1
            else:
                fail_count += 1
            
            # Rate limiting: 요청 간 딜레이 추가
            if index < len(papers):
                time.sleep(1.0)  # 1초 딜레이 (AI 처리 시간 고려)
                
        except Exception as e:
            print(f"[{index}/{len(papers)}] 변환 실패: {str(e)[:100]}")
            print("  ✗ 실패\n")
            fail_count += 1
            continue
    
    return {
        "success": success_count,
        "fail": fail_count,
        "total": len(papers)
    }


async def main_async():
    """
    메인 함수 - 최신 100개 논문 크롤링 (async)
    """
    print("=" * 60)
    print("ArXiv 크롤링 시작 (최신 100개)")
    print("=" * 60)
    
    try:
        # 1. 최신 논문 100개 가져오기
        papers = fetch_latest_papers(max_results=100)
        
        # 2. 논문 처리
        results = await process_papers(papers, mode="latest")
        
        # 3. 결과 통계 출력
        print("\n" + "=" * 60)
        print("크롤링 완료!")
        print("=" * 60)
        print(f"성공: {results['success']}개")
        print(f"실패: {results['fail']}개")
        print(f"전체: {results['total']}개")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n치명적 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """
    메인 함수 - 최신 100개 논문 크롤링
    """
    asyncio.run(main_async())


async def scheduled_crawl_async():
    """
    스케줄링용 크롤링 함수 - 최신 10개 논문 크롤링 (async)
    """
    print("=" * 60)
    print("ArXiv 스케줄링 크롤링 시작 (최신 10개)")
    print("=" * 60)
    
    try:
        # 1. 최신 논문 10개 가져오기
        papers = fetch_scheduled_papers(max_results=10)
        
        # 2. 논문 처리
        results = await process_papers(papers, mode="scheduled")
        
        # 3. 결과 통계 출력
        print("\n" + "=" * 60)
        print("스케줄링 크롤링 완료!")
        print("=" * 60)
        print(f"성공: {results['success']}개")
        print(f"실패: {results['fail']}개")
        print(f"전체: {results['total']}개")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n치명적 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def scheduled_crawl():
    """
    스케줄링용 크롤링 함수 - 최신 10개 논문 크롤링
    """
    asyncio.run(scheduled_crawl_async())


if __name__ == "__main__":
    main()

