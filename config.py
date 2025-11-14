"""
환경변수 및 설정 관리
"""

import os
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv()


# 필수 환경변수
CRAWLER_SECRET_KEY = os.getenv("CRAWLER_SECRET_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 서버 URL
BACKEND_SERVER_URL = os.getenv("BACKEND_SERVER_URL", "http://localhost:8000")
AI_SERVER_URL = os.getenv("AI_SERVER_URL", "https://med-role-alternatives-sol.trycloudflare.com")

# API 엔드포인트
ACTIVITIES_URL = f"{BACKEND_SERVER_URL}/api/crawler/users/activities"
PAPERS_CREATE_URL = f"{BACKEND_SERVER_URL}/api/crawler/papers"
AI_SUMMARIZE_URL = f"{AI_SERVER_URL}/api/summarize-paper"

# Reviewer 설정
REVIEWER_MODEL = os.getenv("REVIEWER_MODEL", "gpt-4o-mini")
REVIEWER_REFLECTION = int(os.getenv("REVIEWER_REFLECTION", "1"))

# 크롤링 설정
ARXIV_QUERY = os.getenv("ARXIV_QUERY", "cat:cs.AI OR cat:cs.LG OR cat:cs.CV")
MAX_RESULTS_LATEST = int(os.getenv("MAX_RESULTS_LATEST", "100"))
MAX_RESULTS_SCHEDULED = int(os.getenv("MAX_RESULTS_SCHEDULED", "10"))

# PDF 처리 설정
MAX_PDF_TEXT_LENGTH = int(os.getenv("MAX_PDF_TEXT_LENGTH", "100000"))

# 타임아웃 설정
PDF_DOWNLOAD_TIMEOUT = int(os.getenv("PDF_DOWNLOAD_TIMEOUT", "30"))
AI_SERVER_TIMEOUT = int(os.getenv("AI_SERVER_TIMEOUT", "120"))
BACKEND_TIMEOUT = int(os.getenv("BACKEND_TIMEOUT", "60"))

# Rate Limiting
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "1.0"))

# ArXiv API Rate Limiting
ARXIV_MAX_RETRIES = int(os.getenv("ARXIV_MAX_RETRIES", "5"))
ARXIV_INITIAL_DELAY = float(os.getenv("ARXIV_INITIAL_DELAY", "3.0"))
ARXIV_CLIENT_DELAY = float(os.getenv("ARXIV_CLIENT_DELAY", "3.0"))


# 환경변수 검증
def validate_config():
    """필수 환경변수가 설정되어 있는지 검증"""
    if not CRAWLER_SECRET_KEY:
        raise ValueError("CRAWLER_SECRET_KEY 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
    
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요.")


# 설정 검증 실행
validate_config()

