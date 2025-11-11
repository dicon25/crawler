"""
ArXiv 논문 크롤러 메인 실행 파일
"""

import asyncio
import sys
import time

from arxiv_fetcher import fetch_latest_papers, fetch_scheduled_papers, transform_arxiv_to_paper_data
from pdf_handler import download_pdf
from paper_reviewer_handler import initialize_reviewer, review_paper
from ai_service import summarize_paper_with_ai
from backend_service import fetch_user_activities, upload_paper_to_backend
from models import CrawlStats
from config import REQUEST_DELAY
from logger import setup_logger, log_section

logger = setup_logger("main")


async def process_single_paper(
    paper,
    reviewer,
    index: int,
    total: int
) -> bool:
    """
    단일 논문 처리
    
    Args:
        paper: ArXiv Result 객체
        reviewer: Reviewer 인스턴스 또는 None
        index: 현재 인덱스
        total: 전체 개수
    
    Returns:
        성공 여부
    """
    paper_start_time = time.time()
    
    try:
        # ArXiv 결과를 PaperData 형식으로 변환
        paper_data = transform_arxiv_to_paper_data(paper)
        
        title_display = paper_data['title'][:50] + "..." if len(paper_data['title']) > 50 else paper_data['title']
        print(f"[{index}/{total}] 처리 중: \"{title_display}\"")
        
        logger.info("=" * 80)
        logger.info(f"논문 처리 시작 [{index}/{total}]")
        logger.info(f"Title: {paper_data['title']}")
        logger.info(f"Paper ID: {paper_data.get('paperId', 'N/A')}")
        logger.info("=" * 80)
        
        # 1단계: PDF 다운로드
        if 'pdfUrl' in paper_data and paper_data['pdfUrl']:
            print("  → PDF 다운로드 중...", end=" ", flush=True)
            logger.info("PDF 다운로드 시작")
            
            download_start = time.time()
            pdf_content = download_pdf(paper_data['pdfUrl'])
            download_time = time.time() - download_start
            
            if pdf_content:
                logger.info(f"PDF 다운로드 완료 (크기: {len(pdf_content)} bytes, 소요 시간: {download_time:.2f}초)")
                print("성공")
            else:
                logger.error(f"PDF 다운로드 실패 (소요 시간: {download_time:.2f}초)")
                print("실패")
                print("  ✗ 실패 (PDF 다운로드 불가)\n")
                return False
        else:
            logger.error("PDF URL 없음")
            print("  ✗ 실패 (PDF URL 없음)\n")
            return False
        
        # 2단계: Reviewer로 논문 적절성 판단
        review_result = None
        if reviewer:
            review_result = await review_paper(pdf_content, reviewer)
            
            if not review_result:
                logger.warning("부적절한 논문으로 판단되어 건너뜀")
                print("  ✗ 부적절한 논문, 건너뜀\n")
                
                paper_elapsed = time.time() - paper_start_time
                logger.info(f"논문 처리 중단 (총 소요 시간: {paper_elapsed:.2f}초)")
                return False
        else:
            logger.info("Reviewer 없음, 모든 논문 적절하다고 판단")
            print("  → Reviewer 없음, 모든 논문 적절하다고 판단")
        
        # 3단계: 적절한 논문이므로 UserActivity 요청
        print("  → 사용자 활동 정보 요청 중...", end=" ", flush=True)
        activities = fetch_user_activities()
        
        if activities:
            print("성공")
        else:
            print("실패 (계속 진행)")
            logger.warning("사용자 활동 정보 가져오기 실패, AI 요약 없이 진행")
        
        # 4단계: AI 서버로 논문 요약 요청 (적절한 논문만)
        ai_response = None
        if activities:
            ai_response = summarize_paper_with_ai(
                pdf_content,
                activities,
                paper_data.get('paperId', f'paper_{index}')
            )
        else:
            logger.warning("사용자 활동 정보 없음, AI 요약 건너뜀")
            print("  ⚠ 경고: 사용자 활동 정보 없음, AI 요약 건너뜀")
        
        # 5단계: 백엔드 서버로 업로드
        success = upload_paper_to_backend(paper_data, pdf_content, ai_response)
        
        paper_elapsed = time.time() - paper_start_time
        
        if success:
            logger.info(f"논문 처리 완료 (총 소요 시간: {paper_elapsed:.2f}초)")
            logger.info("✓ 성공")
            print("  ✓ 완료\n")
            return True
        else:
            logger.error(f"논문 처리 실패 (총 소요 시간: {paper_elapsed:.2f}초)")
            logger.error("✗ 실패")
            print("  ✗ 실패\n")
            return False
            
    except Exception as e:
        paper_elapsed = time.time() - paper_start_time
        logger.error(f"논문 처리 중 오류 발생 (소요 시간: {paper_elapsed:.2f}초)", exc_info=True)
        print(f"  ✗ 실패 (오류: {str(e)[:100]})\n")
        return False


async def process_papers(papers, mode: str = "latest") -> CrawlStats:
    """
    논문 목록 처리
    
    Args:
        papers: ArXiv Result 객체 리스트
        mode: 처리 모드 ("latest" 또는 "scheduled")
    
    Returns:
        처리 결과 통계
    """
    process_start_time = time.time()
    
    log_section(logger, f"논문 처리 시작 (모드: {mode})")
    logger.info(f"처리할 논문 수: {len(papers) if papers else 0}")
    
    if not papers:
        print("가져올 논문이 없습니다.")
        logger.warning("처리할 논문이 없음")
        return {"success": 0, "fail": 0, "total": 0}
    
    print(f"\n논문 {len(papers)}개 발견\n")
    
    # Reviewer 초기화
    reviewer = initialize_reviewer()
    
    # 각 논문 처리
    success_count = 0
    fail_count = 0
    
    for index, paper in enumerate(papers, start=1):
        # 각 논문마다 적절성 판단 후 UserActivity 요청
        result = await process_single_paper(paper, reviewer, index, len(papers))
        
        if result:
            success_count += 1
        else:
            fail_count += 1
        
        logger.info(f"진행 상황: {success_count + fail_count}/{len(papers)} (성공: {success_count}, 실패: {fail_count})")
        
        # Rate limiting: 요청 간 딜레이 추가
        if index < len(papers):
            time.sleep(REQUEST_DELAY)
    
    process_elapsed = time.time() - process_start_time
    
    logger.info("=" * 80)
    logger.info("논문 처리 완료")
    logger.info(f"성공: {success_count}/{len(papers)}")
    logger.info(f"실패: {fail_count}/{len(papers)}")
    logger.info(f"총 소요 시간: {process_elapsed:.2f}초 ({process_elapsed/60:.2f}분)")
    logger.info(f"논문당 평균 소요 시간: {process_elapsed/len(papers):.2f}초")
    logger.info("=" * 80)
    
    return {
        "success": success_count,
        "fail": fail_count,
        "total": len(papers)
    }


async def main_async():
    """
    메인 함수 - 최신 100개 논문 크롤링 (async)
    """
    start_time = time.time()
    
    print("=" * 60)
    print("ArXiv 크롤링 시작 (최신 100개)")
    print("=" * 60)
    
    log_section(logger, "ArXiv 크롤링 시작 (최신 100개)")
    
    try:
        # 1. 최신 논문 가져오기
        papers = fetch_latest_papers()
        
        # 2. 논문 처리
        results = await process_papers(papers, mode="latest")
        
        elapsed = time.time() - start_time
        
        # 3. 결과 통계 출력
        print("\n" + "=" * 60)
        print("크롤링 완료!")
        print("=" * 60)
        print(f"성공: {results['success']}개")
        print(f"실패: {results['fail']}개")
        print(f"전체: {results['total']}개")
        print(f"총 소요 시간: {elapsed:.2f}초 ({elapsed/60:.2f}분)")
        print("=" * 60)
        
        log_section(logger, "크롤링 완료")
        logger.info(f"성공: {results['success']}개")
        logger.info(f"실패: {results['fail']}개")
        logger.info(f"전체: {results['total']}개")
        logger.info(f"총 소요 시간: {elapsed:.2f}초 ({elapsed/60:.2f}분)")
        
    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단되었습니다.")
        logger.warning("사용자에 의해 중단됨")
        sys.exit(1)
    except Exception as e:
        print(f"\n치명적 오류 발생: {e}")
        logger.critical(f"치명적 오류 발생: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def scheduled_crawl_async():
    """
    스케줄링용 크롤링 함수 - 최신 10개 논문 크롤링 (async)
    """
    start_time = time.time()
    
    print("=" * 60)
    print("ArXiv 스케줄링 크롤링 시작 (최신 10개)")
    print("=" * 60)
    
    log_section(logger, "ArXiv 스케줄링 크롤링 시작 (최신 10개)")
    
    try:
        # 1. 최신 논문 가져오기
        papers = fetch_scheduled_papers()
        
        # 2. 논문 처리
        results = await process_papers(papers, mode="scheduled")
        
        elapsed = time.time() - start_time
        
        # 3. 결과 통계 출력
        print("\n" + "=" * 60)
        print("스케줄링 크롤링 완료!")
        print("=" * 60)
        print(f"성공: {results['success']}개")
        print(f"실패: {results['fail']}개")
        print(f"전체: {results['total']}개")
        print(f"총 소요 시간: {elapsed:.2f}초 ({elapsed/60:.2f}분)")
        print("=" * 60)
        
        log_section(logger, "스케줄링 크롤링 완료")
        logger.info(f"성공: {results['success']}개")
        logger.info(f"실패: {results['fail']}개")
        logger.info(f"전체: {results['total']}개")
        logger.info(f"총 소요 시간: {elapsed:.2f}초 ({elapsed/60:.2f}분)")
        
    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단되었습니다.")
        logger.warning("사용자에 의해 중단됨")
        sys.exit(1)
    except Exception as e:
        print(f"\n치명적 오류 발생: {e}")
        logger.critical(f"치명적 오류 발생: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """메인 함수 - 최신 100개 논문 크롤링"""
    asyncio.run(main_async())


def scheduled_crawl():
    """스케줄링용 크롤링 함수 - 최신 10개 논문 크롤링"""
    asyncio.run(scheduled_crawl_async())


if __name__ == "__main__":
    main()

