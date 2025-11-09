# ArXiv 논문 크롤러 with Review System

ArXiv에서 최신 논문을 가져와 AI 리뷰를 생성하고 백엔드 API를 통해 데이터베이스에 저장하는 Python 스크립트입니다.

## 주요 기능

### 1. 논문 크롤링
- **1분마다 자동 실행**: 최신 논문을 지속적으로 모니터링
- **모든 분야 크롤링**: ArXiv의 모든 카테고리에서 최신 논문 수집
- **중복 방지**: 이미 처리된 논문은 자동으로 건너뜀 (`processed_papers.json`에 저장)

### 2. AI 논문 리뷰 생성
- **paper-reviewer 통합**: paper-reviewer 프로젝트의 리뷰 방식을 그대로 채택
- **PDF 텍스트 추출**: 논문 PDF에서 텍스트를 자동으로 추출하여 리뷰 생성
- **마크다운 JSON 파싱**: OpenAI 응답이 마크다운 형태의 JSON인 경우도 안전하게 처리
- **리플렉션 기반 리뷰**: 초기 리뷰 생성 후 3회의 리플렉션을 통해 리뷰 품질 향상
- **앙상블 리뷰**: 여러 리뷰를 종합하여 최종 리뷰 생성

### 3. 백엔드 연동
- 논문 메타데이터와 리뷰를 함께 백엔드 API로 전송
- PDF 파일 자동 업로드

## 설치

```bash
pip install -r requirements.txt
```

## 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 다음 내용을 추가하세요:

```env
# 백엔드 API URL (선택사항, 기본값: http://localhost:8000/api/crawler/papers)
API_BASE_URL=http://localhost:8000/api/crawler/papers

# 크롤러 인증용 시크릿 키 (필수)
CRAWLER_SECRET_KEY=your-secret-key-here

# OpenAI API 키 (필수 - 리뷰 생성에 사용)
OPENAI_API_KEY=your-openai-api-key-here
```

또는 환경변수로 직접 설정할 수도 있습니다:

```bash
export CRAWLER_SECRET_KEY="your-secret-key"
export OPENAI_API_KEY="your-openai-api-key"
```

Windows의 경우:
```cmd
set CRAWLER_SECRET_KEY=your-secret-key
set OPENAI_API_KEY=your-openai-api-key
```

## 사용법

### 리뷰 기능이 포함된 크롤러 실행

```bash
python arxiv_crawler_with_review.py
```

이 스크립트는:
1. 1분마다 ArXiv에서 최신 논문을 검색
2. 새로운 논문에 대해 PDF를 다운로드하고 텍스트 추출
3. AI를 사용하여 논문 리뷰 생성
4. 논문 메타데이터와 리뷰를 백엔드 API로 전송
5. 처리된 논문 ID를 저장하여 중복 처리 방지

### 기존 크롤러 (리뷰 없이)

```bash
python arxiv_crawler.py
```

## 파일 구조

```
arxiv-crawling/
├── arxiv_crawler.py              # 기존 크롤러 (리뷰 없음)
├── arxiv_crawler_with_review.py   # 리뷰 기능이 포함된 크롤러
├── reviewer.py                    # Reviewer 클래스 (paper-reviewer에서 통합)
├── prompts/
│   └── paper_review/             # 리뷰 생성용 프롬프트 파일들
│       ├── reviewer_system.txt
│       ├── paper_review.txt
│       ├── neurips_reviewer_guidelines.txt
│       ├── few_shot_review_examples.txt
│       ├── paper_reflection.txt
│       └── ensemble_system.txt
├── processed_papers.json         # 처리된 논문 ID 저장 (자동 생성)
└── requirements.txt
```

## 주요 기능 상세

### 마크다운 JSON 파싱

OpenAI의 응답이 다음과 같은 형태일 수 있습니다:
- 일반 JSON: `{"key": "value"}`
- 마크다운 코드 블록: ` ```json {"key": "value"} ``` `
- 코드 블록 없이 JSON: `{...}`

`parse_markdown_json()` 함수가 이러한 모든 경우를 처리합니다.

### PDF 텍스트 추출

- PyPDF2를 사용하여 PDF에서 텍스트 추출
- 텍스트가 너무 길 경우 (100,000자 이상) 앞부분만 사용하여 토큰 제한 고려
- 추출 실패 시 빈 문자열 반환 (리뷰 없이 논문만 업로드)

### 리뷰 생성 프로세스

1. **초기 리뷰 생성**: 논문 텍스트를 기반으로 첫 번째 리뷰 생성
2. **리플렉션 (3회)**: 리뷰를 개선하기 위해 3회의 리플렉션 수행
3. **앙상블**: 모든 리뷰를 종합하여 최종 리뷰 생성
4. **리뷰 형식**: NeurIPS 리뷰 가이드라인을 따르는 JSON 형식

## API 엔드포인트

- **URL**: `POST http://localhost:8000/api/crawler/papers`
- **인증**: Bearer 토큰 (CRAWLER_SECRET_KEY 환경변수)
- **Content-Type**: multipart/form-data
- **요청 본문**:
  - `paperId`: 논문 ID
  - `title`: 제목
  - `categories`: 카테고리 (JSON 문자열)
  - `authors`: 저자 목록 (JSON 문자열)
  - `summary`: 초록
  - `doi`: DOI
  - `url`: ArXiv URL
  - `issuedAt`: 발행일
  - `content`: 리뷰 포함 메타데이터 (JSON 문자열)
  - `pdf`: PDF 파일

## 설정 변경

`arxiv_crawler_with_review.py`의 `fetch_latest_arxiv_papers()` 함수에서 다음 설정을 변경할 수 있습니다:

- `max_results`: 가져올 최대 논문 수 (기본값: 50)
- `sort_by`: 정렬 기준 (기본값: SubmittedDate)
- `sort_order`: 정렬 순서 (기본값: Descending)

`process_new_papers()` 함수에서:
- 크롤링 주기: `main()` 함수의 `await asyncio.sleep(60)` 값 변경 (기본값: 60초 = 1분)

## 주의사항

- **Rate Limiting**: ArXiv API와 OpenAI API 사용 시 Rate Limiting을 위해 요청 간 딜레이가 추가됩니다.
- **토큰 사용량**: 리뷰 생성 시 OpenAI API 토큰이 소모됩니다. 비용을 고려하여 사용하세요.
- **PDF 다운로드**: 일부 논문의 PDF 다운로드가 실패할 수 있습니다. 이 경우 리뷰 없이 메타데이터만 업로드됩니다.
- **처리 시간**: 리뷰 생성에 시간이 걸리므로 논문당 약 1-2분 정도 소요될 수 있습니다.
- **중복 방지**: `processed_papers.json` 파일을 삭제하면 모든 논문을 다시 처리합니다.
- **에러 처리**: 네트워크 오류나 API 오류 발생 시 해당 논문은 건너뛰고 계속 진행됩니다.

## 문제 해결

### OpenAI API 키 오류
```
ValueError: OPENAI_API_KEY environment variable is not set.
```
→ `.env` 파일에 `OPENAI_API_KEY`를 추가하거나 환경변수로 설정하세요.

### PDF 텍스트 추출 실패
→ PyPDF2가 일부 PDF 형식을 지원하지 않을 수 있습니다. 이 경우 리뷰 없이 논문만 업로드됩니다.

### JSON 파싱 오류
→ `parse_markdown_json()` 함수가 자동으로 처리하지만, 여전히 실패하는 경우 리뷰 생성이 건너뛰어집니다.

