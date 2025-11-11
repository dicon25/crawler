"""
논문 리뷰 처리 모듈
"""

import time
from typing import Dict, Optional

from reviewer import Reviewer
from pdf_handler import extract_text_from_pdf
from config import REVIEWER_MODEL, REVIEWER_REFLECTION
from logger import setup_logger

logger = setup_logger("reviewer")


async def review_paper(pdf_content: bytes, reviewer: Reviewer) -> Optional[Dict]:
    """
    Reviewer를 사용하여 논문이 적절한지 판단
    
    Args:
        pdf_content: PDF 파일의 바이너리 데이터
        reviewer: Reviewer 인스턴스
    
    Returns:
        리뷰 결과 (적절한 논문이면 리뷰 데이터, 아니면 None)
    """
    start_time = time.time()
    logger.info("=" * 80)
    logger.info("Reviewer: 논문 적절성 판단 시작")
    logger.info("=" * 80)
    
    try:
        # PDF에서 텍스트 추출
        logger.debug(f"PDF 크기: {len(pdf_content)} bytes")
        paper_text = extract_text_from_pdf(pdf_content)
        
        if not paper_text:
            logger.warning("PDF 텍스트 추출 실패")
            print("    ⚠ 텍스트 추출 실패, 리뷰 건너뜀")
            return None
        
        logger.info(f"PDF 텍스트 추출 완료: {len(paper_text)} 문자")
        logger.debug(f"텍스트 미리보기: {paper_text[:200]}...")
        
        # Reviewer로 논문 리뷰
        print("  → Reviewer로 논문 적절성 판단 중...", end=" ", flush=True)
        logger.info(f"OpenAI API 호출 시작 (Model: {REVIEWER_MODEL}, Reflection: {REVIEWER_REFLECTION})")
        
        review_start = time.time()
        reviews = await reviewer.review(paper_text, reflection=REVIEWER_REFLECTION)
        review_time = time.time() - review_start
        
        logger.info(f"OpenAI API 호출 완료 (소요 시간: {review_time:.2f}초)")
        
        # 토큰 사용량 로깅 (Reviewer 객체에서 가져올 수 있다면)
        if hasattr(reviewer, 'last_usage'):
            usage = reviewer.last_usage
            from logger import log_cost
            log_cost(logger, REVIEWER_MODEL, usage.get('prompt_tokens', 0), usage.get('completion_tokens', 0))
        
        if not reviews or len(reviews) == 0:
            logger.warning("리뷰 결과가 비어있음")
            print("실패 (리뷰 없음)")
            return None
        
        # 첫 번째 리뷰 결과 확인
        review_result = reviews[0]
        logger.debug(f"리뷰 결과: {review_result}")
        
        # 논문이 적절한지 판단
        is_appropriate = False  # 기본값을 False로 변경
        
        # 1. recommendation 필드 체크 (최우선)
        if 'recommendation' in review_result:
            recommendation = review_result.get('recommendation', '').lower()
            logger.info(f"Recommendation: {review_result.get('recommendation')}")
            
            # Accept 계열이면 적절
            if 'accept' in recommendation:
                is_appropriate = True
            # Reject 계열이면 부적절
            elif 'reject' in recommendation:
                is_appropriate = False
            else:
                logger.warning(f"알 수 없는 recommendation 값: {recommendation}")
        
        # 2. overall_score 필드 체크
        if 'overall_score' in review_result:
            overall_score = review_result.get('overall_score', 0)
            logger.info(f"Overall Score: {overall_score}/10")
            
            # recommendation이 없었다면 overall_score로 판단
            if 'recommendation' not in review_result:
                is_appropriate = overall_score >= 5
        
        # 3. rating 필드 체크 (하위 호환성)
        if 'rating' in review_result:
            rating = review_result.get('rating', 0)
            logger.info(f"Rating: {rating}/10")
            
            # recommendation과 overall_score 둘 다 없었다면 rating으로 판단
            if 'recommendation' not in review_result and 'overall_score' not in review_result:
                is_appropriate = rating >= 5
        
        # 판단 결과 로깅
        logger.info(f"적절성 판단: {'적절' if is_appropriate else '부적절'}")
        
        if 'content' in review_result:
            logger.info(f"리뷰 내용 (처음 300자): {review_result['content'][:300]}...")
        
        elapsed = time.time() - start_time
        logger.info(f"Reviewer 총 소요 시간: {elapsed:.2f}초")
        
        if is_appropriate:
            print("성공 (적절한 논문)")
            logger.info("✓ 적절한 논문으로 판단됨")
            return review_result
        else:
            print(f"부적절 (recommendation: {review_result.get('recommendation', 'N/A')}, score: {review_result.get('overall_score', review_result.get('rating', 'N/A'))})")
            logger.info(f"✗ 부적절한 논문으로 판단됨")
            return None
            
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Reviewer 오류 발생: {str(e)}", exc_info=True)
        logger.error(f"소요 시간: {elapsed:.2f}초")
        print(f"실패 (오류: {str(e)[:100]})")
        return None


def initialize_reviewer() -> Optional[Reviewer]:
    """
    Reviewer 초기화
    
    Returns:
        Reviewer 인스턴스 또는 None
    """
    try:
        print("Reviewer 초기화 중...")
        logger.info("=" * 80)
        logger.info("Reviewer 초기화 시작")
        logger.info(f"Model: {REVIEWER_MODEL}")
        logger.info(f"Reflection: {REVIEWER_REFLECTION}")
        logger.info("=" * 80)
        
        reviewer = Reviewer(model=REVIEWER_MODEL)
        
        print("Reviewer 초기화 완료\n")
        logger.info("Reviewer 초기화 성공")
        return reviewer
    except Exception as e:
        print(f"⚠ 경고: Reviewer 초기화 실패: {str(e)[:100]}")
        logger.error(f"Reviewer 초기화 실패: {str(e)}", exc_info=True)
        print("Reviewer 없이 진행합니다 (모든 논문을 적절하다고 판단).\n")
        logger.warning("Reviewer 없이 진행 - 모든 논문을 적절하다고 판단")
        return None

