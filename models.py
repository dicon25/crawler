"""
데이터 모델 및 타입 정의
"""

from typing import Dict, List, Optional, TypedDict


class PaperData(TypedDict):
    """논문 데이터 타입"""
    paperId: str
    title: str
    categories: str  # JSON string
    authors: str  # JSON string
    summary: str
    doi: str
    url: str
    pdfUrl: str
    issuedAt: str


class AIResponse(TypedDict, total=False):
    """AI 서버 응답 타입"""
    summary: str
    translatedSummary: str
    thumbnail: str  # base64
    thumbnail_bytes: bytes  # decoded
    tableOfContents: List[Dict]
    contents: List[Dict]
    hashtags: List[Dict]
    interestedUsers: List[Dict]
    content: str  # JSON string


class ProcessedAIResponse(TypedDict, total=False):
    """처리된 AI 응답 타입"""
    summary: str
    translatedSummary: str
    content: str  # JSON string (tableOfContents + contents)
    hashtags: str  # JSON string
    interestedUsers: str  # JSON string (userId array)
    thumbnail_bytes: bytes


class ReviewResult(TypedDict, total=False):
    """리뷰 결과 타입"""
    rating: int
    summary: str
    strengths: List[str]
    weaknesses: List[str]
    questions: List[str]


class CrawlStats(TypedDict):
    """크롤링 통계 타입"""
    success: int
    fail: int
    total: int

