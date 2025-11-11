# ArXiv 논문 크롤러

ArXiv에서 최신 논문을 가져와 Reviewer로 적절성을 판단하고, AI 서버를 통해 요약 및 분석한 후, 백엔드 API를 통해 데이터베이스에 저장하는 Python 스크립트입니다.

## 프로젝트 구조

```
scholub/crawler/
├── main.py                      # 메인 실행 파일 ⭐
├── config.py                    # 환경변수 및 설정 관리
├── models.py                    # 데이터 타입 정의
├── arxiv_fetcher.py            # ArXiv 논문 가져오기
├── pdf_handler.py              # PDF 다운로드 및 텍스트 추출
├── paper_reviewer_handler.py   # Reviewer 로직
├── ai_service.py               # AI 서버 통신
├── backend_service.py          # 백엔드 서버 통신
├── reviewer.py                 # Reviewer 클래스
├── prompts/                    # Reviewer 프롬프트 파일들
│   └── paper_review/
├── thumbnail.webp              # 기본 썸네일 이미지
├── mockdata.json              # 목데이터 (필요시)
├── requirements.txt           # Python 패키지 의존성
├── env.example.txt            # 환경변수 예시
├── README.md                  # 프로젝트 문서
└── old_arxiv_crawler.py       # 이전 버전 (백업용)
```

## 논문 처리 흐름

```
1. ArXiv에서 논문 메타데이터 가져오기
   ↓
2. PDF 다운로드
   ↓
3. Reviewer로 논문 적절성 판단 ⭐
   ↓ (적절한 논문만)
4. Backend Server에서 UserActivity 요청
   ↓
5. AI Server로 PDF + UserActivity 전송
   ↓
6. AI Server Response 가공
   - summary, translatedSummary
   - tableOfContents, contents
   - hashtags
   - interestedUsers (userId 배열)
   - thumbnail (base64 → bytes)
   ↓
7. Backend Server로 전송
```

## 설치

```bash
pip install -r requirements.txt
```

## 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성하세요. `env.example.txt`를 참고하세요.

### 필수 환경변수

```env
# 크롤러 인증용 시크릿 키 (백엔드에서 발급)
CRAWLER_SECRET_KEY=your-secret-key-here

# OpenAI API 키 (Reviewer 사용)
OPENAI_API_KEY=your-openai-api-key-here
```

### 선택적 환경변수 (기본값 있음)

```env
# 서버 URL
BACKEND_SERVER_URL=http://localhost:8000
AI_SERVER_URL=https://med-role-alternatives-sol.trycloudflare.com

# Reviewer 설정
REVIEWER_MODEL=gpt-4o-mini          # OpenAI 모델
REVIEWER_REFLECTION=1                # Reflection 횟수 (빠른 판단)

# 크롤링 설정
ARXIV_QUERY=cat:cs.AI OR cat:cs.LG OR cat:cs.CV
MAX_RESULTS_LATEST=100               # 최신 논문 크롤링 시 가져올 개수
MAX_RESULTS_SCHEDULED=10             # 스케줄링 크롤링 시 가져올 개수

# PDF 처리
MAX_PDF_TEXT_LENGTH=100000           # PDF 텍스트 최대 길이

# 타임아웃 (초 단위)
PDF_DOWNLOAD_TIMEOUT=30
AI_SERVER_TIMEOUT=120
BACKEND_TIMEOUT=60

# Rate Limiting
REQUEST_DELAY=1.0                    # 요청 간 딜레이 (초)
```

## 사용법

### 1. 최신 100개 논문 크롤링

```bash
python main.py
```

### 2. 스케줄링용 크롤링 (Python)

```python
from main import scheduled_crawl

# 최신 10개 논문 크롤링
scheduled_crawl()
```

### 3. 스케줄링용 크롤링 (Cron)

```bash
# 매 시간마다 실행
0 * * * * cd /path/to/scholub/crawler && python -c "from main import scheduled_crawl; scheduled_crawl()"
```

## 모듈 설명

### `config.py`
- 환경변수 로드 및 관리
- API 엔드포인트 URL 구성
- 필수 환경변수 검증

### `models.py`
- 데이터 타입 정의 (TypedDict)
- `PaperData`, `AIResponse`, `ReviewResult` 등

### `arxiv_fetcher.py`
- ArXiv API 통신
- 논문 검색 및 메타데이터 변환
- 카테고리 코드 → 사람이 읽을 수 있는 이름으로 변환

### `pdf_handler.py`
- PDF 다운로드
- PDF 텍스트 추출 (PyPDF2)
- 기본 썸네일 로드

### `paper_reviewer_handler.py`
- Reviewer 초기화
- 논문 적절성 판단
- rating 기반 필터링 (기본: rating ≥ 5)

### `ai_service.py`
- AI 서버 통신
- AI 응답 처리 및 가공
  - thumbnail base64 디코딩
  - interestedUsers에서 userId 추출
  - tableOfContents + contents → content 통합

### `backend_service.py`
- 백엔드 서버 통신
- 사용자 활동 정보 가져오기
- 논문 데이터 업로드

### `main.py`
- 메인 실행 로직
- 논문 처리 파이프라인 조율
- 통계 출력

## API 엔드포인트

### 1. 사용자 활동 정보 가져오기
```
GET {BACKEND_SERVER_URL}/api/crawler/users/activities
Authorization: Bearer {CRAWLER_SECRET_KEY}
```

### 2. AI 서버로 논문 요약 요청
```
POST {AI_SERVER_URL}/api/summarize-paper
Content-Type: multipart/form-data

file: [PDF 파일]
activity: [JSON.stringify(활동 정보)]
```

**응답 예시:**
```json
{
  "summary": "Paper Summary",
  "translatedSummary": "논문 요약",
  "thumbnail": "base64 encoded image",
  "tableOfContents": [...],
  "contents": [...],
  "hashtags": [...],
  "interestedUsers": [{"userId": "abc", ...}]
}
```

### 3. 백엔드로 논문 업로드
```
POST {BACKEND_SERVER_URL}/api/crawler/papers
Authorization: Bearer {CRAWLER_SECRET_KEY}
Content-Type: multipart/form-data

paperId, title, categories, authors, summary, translatedSummary,
doi, url, issuedAt, content, hashtags, interestedUsers,
pdf (file), thumbnail (file)
```

## 설정 변경

### Reviewer 적절성 판단 기준
`paper_reviewer_handler.py`의 `review_paper()` 함수:
```python
# 기본: rating 5 이상
is_appropriate = rating >= 5

# 더 엄격하게: rating 7 이상
is_appropriate = rating >= 7
```

### Reflection 횟수 조정
`.env` 파일:
```env
# 빠른 판단 (기본)
REVIEWER_REFLECTION=1

# 정확한 판단
REVIEWER_REFLECTION=3
```

### 크롤링 개수 조정
`.env` 파일:
```env
# 최신 논문 크롤링 개수
MAX_RESULTS_LATEST=50

# 스케줄링 크롤링 개수
MAX_RESULTS_SCHEDULED=5
```

## 주의사항

- **필수 환경변수**: `CRAWLER_SECRET_KEY`, `OPENAI_API_KEY` 반드시 설정
- **Rate Limiting**: ArXiv API 사용 시 요청 간 딜레이 적용
- **AI 처리 시간**: 논문당 약 1-2분 소요
- **Reviewer**: OpenAI API 토큰 소모 (비용 고려)
- **PDF 다운로드**: 일부 논문 다운로드 실패 가능

## 문제 해결

### 환경변수 오류
```
ValueError: CRAWLER_SECRET_KEY 환경변수가 설정되지 않았습니다.
```
→ `.env` 파일에 `CRAWLER_SECRET_KEY`를 추가하세요.

### Reviewer 초기화 실패
```
ValueError: OPENAI_API_KEY environment variable is not set.
```
→ `.env` 파일에 `OPENAI_API_KEY`를 추가하세요.

### PDF 다운로드 실패
```
PDF 다운로드 실패: ...
```
→ 네트워크 문제 또는 ArXiv 서버 문제. 잠시 후 다시 시도하세요.

### AI 서버 타임아웃
```
실패 (네트워크 오류: timeout)
```
→ `.env`에서 `AI_SERVER_TIMEOUT` 값을 증가시키세요 (예: 180).

## 개발자 정보

이 프로젝트는 ArXiv 논문을 자동으로 수집하고, Reviewer로 적절성을 판단하며, AI를 활용하여 분석한 후, 백엔드 시스템과 연동하여 사용자에게 맞춤형 논문 추천을 제공하는 것을 목표로 합니다.

## 라이센스

MIT License
