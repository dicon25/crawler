"""
PDF 다운로드 및 텍스트 추출 모듈
"""

import io
from typing import Optional

import PyPDF2
import requests

from config import PDF_DOWNLOAD_TIMEOUT, MAX_PDF_TEXT_LENGTH


def download_pdf(pdf_url: str) -> Optional[bytes]:
    """
    PDF 파일을 다운로드하는 함수
    
    Args:
        pdf_url: PDF 파일의 URL
    
    Returns:
        PDF 파일의 바이너리 데이터 또는 None
    """
    try:
        response = requests.get(pdf_url, timeout=PDF_DOWNLOAD_TIMEOUT)
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
        if len(text) > MAX_PDF_TEXT_LENGTH:
            text = text[:MAX_PDF_TEXT_LENGTH]
        
        return text
    except Exception as e:
        print(f"    ⚠ 경고: PDF 텍스트 추출 실패: {str(e)[:50]}")
        return ""


def load_thumbnail() -> Optional[bytes]:
    """
    thumbnail.webp 파일을 로드하는 함수
    
    Returns:
        thumbnail.webp 파일의 바이너리 데이터 또는 None
    """
    import os
    
    try:
        thumbnail_path = os.path.join(os.path.dirname(__file__), "thumbnail.webp")
        with open(thumbnail_path, "rb") as f:
            return f.read()
    except FileNotFoundError:
        print("경고: thumbnail.webp 파일을 찾을 수 없습니다.")
        return None

