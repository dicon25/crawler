"""
ArXiv 논문 크롤러
ArXiv에서 논문을 가져와 백엔드 API를 통해 데이터베이스에 저장하는 스크립트
"""

import arxiv
import requests
import os
import json
from datetime import datetime
from typing import List, Dict, Optional
import time
import sys
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv()

# API 설정
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/crawler/papers")
CRAWLER_SECRET_KEY = os.getenv("CRAWLER_SECRET_KEY")

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
    # content는 나중에 mockdata.json에서 로드하므로 여기서는 설정하지 않음
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


def load_mockdata() -> Dict:
    """
    mockdata.json 파일을 로드하는 함수
    
    Returns:
        mockdata.json의 내용 (딕셔너리)
    """
    try:
        mockdata_path = os.path.join(os.path.dirname(__file__), "mockdata.json")
        with open(mockdata_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("경고: mockdata.json 파일을 찾을 수 없습니다. 빈 객체를 사용합니다.")
        return {}
    except json.JSONDecodeError as e:
        print(f"경고: mockdata.json 파싱 오류: {e}. 빈 객체를 사용합니다.")
        return {}


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


def upload_paper(paper_data: Dict, index: int, total: int) -> bool:
    """
    API를 통해 논문 업로드
    
    Args:
        paper_data: 논문 데이터 딕셔너리
        index: 현재 인덱스 (1부터 시작)
        total: 전체 개수
    
    Returns:
        성공 여부 (bool)
    """
    title_display = paper_data['title'][:50] + "..." if len(paper_data['title']) > 50 else paper_data['title']
    print(f"[{index}/{total}] 업로드 중: \"{title_display}\"", end=" ... ", flush=True)
    
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
                # PDF 파일을 files에 추가
                # 논문 ID를 파일명으로 사용
                paper_id = paper_data.get('paperId', f'paper_{index}')
                files['pdf'] = (f'{paper_id}.pdf', pdf_content, 'application/pdf')
        
        if not pdf_content:
            print("실패 (PDF 다운로드 불가)")
            return False
        
        # thumbnail.webp 파일 로드
        thumbnail_content = load_thumbnail()
        if thumbnail_content:
            files['thumbnail'] = ('thumbnail.webp', thumbnail_content, 'image/webp')
        
        # mockdata.json 로드하여 content 필드에 추가
        mockdata = load_mockdata()
        
        # multipart/form-data 형식으로 데이터 전송
        # 배열 필드(categories, authors)는 JSON 문자열로 전송
        # 백엔드가 배열을 직접 받는다면 이 부분을 수정해야 할 수 있음
        data = {}
        
        # 모든 필드를 data에 추가 (pdfUrl은 제외, pdf 파일로 대체)
        for key, value in paper_data.items():
            if key == 'pdfUrl':  # pdfUrl은 제외 (pdf 파일로 대체)
                continue
            if value is not None and value != "":
                # 문자열로 변환 (이미 JSON 문자열인 경우 그대로 사용)
                if isinstance(value, (list, dict)):
                    data[key] = json.dumps(value)
                else:
                    data[key] = str(value)
        
        # content 필드에 mockdata.json 내용 추가
        data['content'] = json.dumps(mockdata)
        
        response = requests.post(
            API_BASE_URL,
            headers=headers,
            data=data,
            files=files,
            timeout=60  # PDF 업로드 시간을 고려하여 타임아웃 증가
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


def main():
    """
    메인 함수
    """
    print("=" * 60)
    print("ArXiv 크롤링 시작...")
    print("=" * 60)
    
    try:
        # 1. ArXiv에서 논문 가져오기
        papers = fetch_arxiv_papers(
            query="cat:cs.AI OR cat:cs.LG OR cat:cs.CV",
            max_results=100,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending
        )
        
        if not papers:
            print("가져올 논문이 없습니다.")
            return
        
        print(f"\n논문 {len(papers)}개 발견\n")
        
        # 2. 각 논문을 API 형식으로 변환하고 업로드
        success_count = 0
        fail_count = 0
        
        for index, paper in enumerate(papers, start=1):
            try:
                # ArXiv 결과를 API 형식으로 변환
                paper_data = transform_arxiv_to_api_format(paper)
                
                # API를 통해 업로드
                if upload_paper(paper_data, index, len(papers)):
                    success_count += 1
                else:
                    fail_count += 1
                
                # Rate limiting: 요청 간 딜레이 추가
                if index < len(papers):
                    time.sleep(0.5)  # 0.5초 딜레이
                    
            except Exception as e:
                print(f"[{index}/{len(papers)}] 변환 실패: {str(e)[:50]}")
                fail_count += 1
                continue
        
        # 3. 결과 통계 출력
        print("\n" + "=" * 60)
        print("크롤링 완료!")
        print("=" * 60)
        print(f"성공: {success_count}개")
        print(f"실패: {fail_count}개")
        print(f"전체: {len(papers)}개")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n치명적 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

