"""
로깅 설정 모듈
"""

import logging
import sys
from datetime import datetime
from pathlib import Path


def setup_logger(name: str = "crawler") -> logging.Logger:
    """
    로거 설정
    
    Args:
        name: 로거 이름
    
    Returns:
        설정된 로거
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # 이미 핸들러가 있으면 반환 (중복 방지)
    if logger.handlers:
        return logger
    
    # 로그 디렉토리 생성
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # 로그 파일명 (날짜별)
    log_file = log_dir / f"crawler_{datetime.now().strftime('%Y%m%d')}.log"
    
    # 포맷터 설정
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 파일 핸들러 (상세 로그)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # 콘솔 핸들러 (INFO 이상만)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def log_section(logger: logging.Logger, title: str, level: str = "INFO"):
    """
    섹션 구분 로그
    
    Args:
        logger: 로거 인스턴스
        title: 섹션 제목
        level: 로그 레벨
    """
    separator = "=" * 80
    log_func = getattr(logger, level.lower())
    log_func(separator)
    log_func(f" {title}")
    log_func(separator)


def log_dict(logger: logging.Logger, data: dict, title: str = "Data", max_length: int = 500):
    """
    딕셔너리 데이터를 로깅
    
    Args:
        logger: 로거 인스턴스
        data: 로깅할 딕셔너리
        title: 데이터 제목
        max_length: 각 값의 최대 길이
    """
    logger.debug(f"{title}:")
    for key, value in data.items():
        # thumbnail base64는 축약 표시
        if key == 'thumbnail' and isinstance(value, str) and len(value) > 50:
            value_str = "base64..."
        else:
            value_str = str(value)
            if len(value_str) > max_length:
                value_str = value_str[:max_length] + "..."
        logger.debug(f"  {key}: {value_str}")


def log_cost(logger: logging.Logger, model: str, prompt_tokens: int, completion_tokens: int):
    """
    OpenAI API 비용 로깅
    
    Args:
        logger: 로거 인스턴스
        model: 사용한 모델
        prompt_tokens: 프롬프트 토큰 수
        completion_tokens: 완성 토큰 수
    """
    total_tokens = prompt_tokens + completion_tokens
    
    # 모델별 가격 (2024년 기준, USD per 1M tokens)
    pricing = {
        "gpt-4o-mini": {
            "input": 0.15,  # $0.15 per 1M input tokens
            "output": 0.60  # $0.60 per 1M output tokens
        },
        "gpt-4o": {
            "input": 5.00,
            "output": 15.00
        },
        "gpt-4-turbo": {
            "input": 10.00,
            "output": 30.00
        },
        "gpt-3.5-turbo": {
            "input": 0.50,
            "output": 1.50
        }
    }
    
    # 기본값
    price = pricing.get(model, pricing["gpt-4o-mini"])
    
    # 비용 계산
    input_cost = (prompt_tokens / 1_000_000) * price["input"]
    output_cost = (completion_tokens / 1_000_000) * price["output"]
    total_cost = input_cost + output_cost
    
    logger.info(f"OpenAI Usage - Model: {model}")
    logger.info(f"  Prompt Tokens: {prompt_tokens:,}")
    logger.info(f"  Completion Tokens: {completion_tokens:,}")
    logger.info(f"  Total Tokens: {total_tokens:,}")
    logger.info(f"  Cost: ${total_cost:.6f} (Input: ${input_cost:.6f} + Output: ${output_cost:.6f})")

