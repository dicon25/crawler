"""
ArXiv 논문 가져오기 모듈
"""

from typing import Dict, List

import arxiv

from config import ARXIV_QUERY, MAX_RESULTS_LATEST, MAX_RESULTS_SCHEDULED


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
        사람이 읽을 수 있는 카테고리 이름
    """
    return ARXIV_CATEGORY_MAPPING.get(category_code, category_code)


def fetch_arxiv_papers(
    query: str = ARXIV_QUERY,
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


def fetch_latest_papers(max_results: int = MAX_RESULTS_LATEST) -> List[arxiv.Result]:
    """
    최신 논문 가져오기
    
    Args:
        max_results: 가져올 최대 논문 수
    
    Returns:
        ArXiv Result 객체 리스트
    """
    return fetch_arxiv_papers(
        query=ARXIV_QUERY,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending
    )


def fetch_scheduled_papers(max_results: int = MAX_RESULTS_SCHEDULED) -> List[arxiv.Result]:
    """
    스케줄링용 논문 가져오기
    
    Args:
        max_results: 가져올 최대 논문 수
    
    Returns:
        ArXiv Result 객체 리스트
    """
    return fetch_arxiv_papers(
        query=ARXIV_QUERY,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending
    )


def extract_doi_from_result(paper: arxiv.Result) -> str:
    """
    Result 객체에서 DOI를 추출하는 함수
    
    Args:
        paper: arxiv Result 객체
    
    Returns:
        DOI 문자열
    """
    # 방법 1: Result 객체의 doi 속성 직접 확인
    try:
        if hasattr(paper, 'doi') and paper.doi:
            doi = str(paper.doi)
            if not doi.startswith("http"):
                return f"https://doi.org/{doi}"
            return doi
    except (AttributeError, TypeError):
        pass
    
    # 방법 2: feedparser의 entry 객체에서 arxiv_doi 확인
    try:
        if hasattr(paper, '_raw'):
            entry = paper._raw
            if hasattr(entry, 'arxiv_doi') and entry.arxiv_doi:
                doi = str(entry.arxiv_doi)
                if not doi.startswith("http"):
                    return f"https://doi.org/{doi}"
                return doi
        
        if hasattr(paper, 'arxiv_doi') and paper.arxiv_doi:
            doi = str(paper.arxiv_doi)
            if not doi.startswith("http"):
                return f"https://doi.org/{doi}"
            return doi
        
        if hasattr(paper, '__dict__'):
            paper_dict = paper.__dict__
            if '_raw' in paper_dict:
                raw_entry = paper_dict['_raw']
                if hasattr(raw_entry, 'arxiv_doi') and raw_entry.arxiv_doi:
                    doi = str(raw_entry.arxiv_doi)
                    if not doi.startswith("http"):
                        return f"https://doi.org/{doi}"
                    return doi
            
            if 'arxiv_doi' in paper_dict and paper_dict['arxiv_doi']:
                doi = str(paper_dict['arxiv_doi'])
                if not doi.startswith("http"):
                    return f"https://doi.org/{doi}"
                return doi
    except Exception:
        pass
    
    # DOI가 없으면 arXiv ID 사용
    paper_id = paper.entry_id.split('/')[-1] if paper.entry_id else "unknown"
    return f"arXiv:{paper_id}"


def transform_arxiv_to_paper_data(arxiv_result: arxiv.Result) -> Dict:
    """
    ArXiv 결과를 PaperData 형식으로 변환
    
    Args:
        arxiv_result: ArXiv Result 객체
    
    Returns:
        PaperData 딕셔너리
    """
    import json
    
    # 논문 ID 추출
    paper_id = arxiv_result.entry_id.split('/')[-1] if arxiv_result.entry_id else None
    
    if not paper_id:
        raise ValueError("논문 ID를 추출할 수 없습니다.")
    
    # DOI 추출
    doi = extract_doi_from_result(arxiv_result)
    
    # 카테고리 처리
    category_codes = list(arxiv_result.categories) if arxiv_result.categories else []
    categories = [map_category_code_to_name(code) for code in category_codes]
    
    # 저자 목록
    authors = [author.name for author in arxiv_result.authors] if arxiv_result.authors else []
    
    # 발행일 ISO 8601 형식으로 변환
    issued_at = arxiv_result.published.strftime("%Y-%m-%dT%H:%M:%SZ") if arxiv_result.published else ""
    
    # PDF URL 구성
    pdf_url = arxiv_result.entry_id.replace('/abs/', '/pdf/') + '.pdf' if arxiv_result.entry_id else ""
    
    return {
        "paperId": paper_id,
        "title": arxiv_result.title or "",
        "categories": json.dumps(categories),
        "authors": json.dumps(authors),
        "summary": arxiv_result.summary or "",
        "doi": doi,
        "url": arxiv_result.entry_id or "",
        "pdfUrl": pdf_url,
        "issuedAt": issued_at
    }

