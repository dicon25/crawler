"""
백엔드 서버 통신 모듈
"""

import json
import time
from typing import Dict, List, Optional

import requests

from config import ACTIVITIES_URL, PAPERS_CREATE_URL, CRAWLER_SECRET_KEY, BACKEND_TIMEOUT
from models import PaperData, ProcessedAIResponse
from pdf_handler import load_thumbnail
from logger import setup_logger, log_dict

logger = setup_logger("backend")


def fetch_user_activities() -> Optional[List[Dict]]:
    """
    백엔드 서버에서 사용자 활동 정보 가져오기
    
    Returns:
        사용자 활동 목록 또는 None
    """
    start_time = time.time()
    logger.info("=" * 80)
    logger.info("Backend Server: 사용자 활동 정보 요청")
    logger.info("=" * 80)
    
    try:
        headers = {
            "Authorization": f"Bearer {CRAWLER_SECRET_KEY[:10]}..." # 보안을 위해 일부만 로깅
        }
        
        logger.info(f"요청 URL: {ACTIVITIES_URL}")
        logger.debug(f"헤더: Authorization: Bearer {CRAWLER_SECRET_KEY[:10]}...")
        
        request_start = time.time()
        response = requests.get(ACTIVITIES_URL, headers={"Authorization": f"Bearer {CRAWLER_SECRET_KEY}"}, timeout=30)
        request_time = time.time() - request_start
        
        logger.info(f"응답 수신 완료 (소요 시간: {request_time:.2f}초)")
        logger.info(f"응답 상태 코드: {response.status_code}")
        
        response.raise_for_status()
        activities = response.json()
        
        count = len(activities) if isinstance(activities, list) else 1
        logger.info(f"사용자 활동 {count}개 가져오기 성공")
        
        # 활동 정보 상세 로깅 (처음 3개만)
        if isinstance(activities, list) and activities:
            for idx, activity in enumerate(activities[:3]):
                logger.debug(f"Activity {idx + 1}: {activity}")
        
        elapsed = time.time() - start_time
        logger.info(f"Backend Server (Activities) 총 소요 시간: {elapsed:.2f}초")
        logger.info("✓ 사용자 활동 정보 가져오기 완료")
        
        print(f"사용자 활동 {count}개 가져오기 성공")
        return activities
        
    except requests.exceptions.RequestException as e:
        elapsed = time.time() - start_time
        logger.error(f"사용자 활동 가져오기 실패 (소요 시간: {elapsed:.2f}초)")
        logger.error(f"오류: {str(e)}", exc_info=True)
        print(f"경고: 사용자 활동 가져오기 실패: {str(e)[:100]}")
        return None
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"사용자 활동 처리 중 오류 (소요 시간: {elapsed:.2f}초)")
        logger.error(f"오류: {str(e)}", exc_info=True)
        print(f"경고: 사용자 활동 처리 중 오류: {str(e)[:100]}")
        return None


def upload_paper_to_backend(
    paper_data: PaperData,
    pdf_content: bytes,
    ai_response: Optional[ProcessedAIResponse]
) -> bool:
    """
    백엔드 API를 통해 논문 업로드
    
    Args:
        paper_data: 논문 데이터
        pdf_content: PDF 파일의 바이너리 데이터
        ai_response: AI 서버 응답 (처리된 데이터)
    
    Returns:
        성공 여부 (bool)
    """
    start_time = time.time()
    logger.info("=" * 80)
    logger.info("Backend Server: 논문 업로드 요청")
    logger.info("=" * 80)
    
    try:
        paper_id = paper_data.get('paperId', 'unknown')
        logger.info(f"Paper ID: {paper_id}")
        logger.info(f"Title: {paper_data.get('title', 'N/A')[:100]}")
        
        headers = {
            "Authorization": f"Bearer {CRAWLER_SECRET_KEY}"
        }
        
        # multipart/form-data 형식으로 데이터 전송
        data = {}
        files = {}
        
        # 기본 논문 데이터 추가 (pdfUrl과 translatedSummary는 제외)
        logger.debug("기본 논문 데이터 준비:")
        for key, value in paper_data.items():
            if key in ['pdfUrl', 'translatedSummary']:
                continue
            if value is not None and value != "":
                if isinstance(value, (list, dict)):
                    data[key] = json.dumps(value)
                else:
                    data[key] = str(value)
                
                # 로깅 (긴 값은 잘라서)
                value_str = str(data[key])
                if len(value_str) > 100:
                    logger.debug(f"  {key}: {value_str[:100]}...")
                else:
                    logger.debug(f"  {key}: {value_str}")
        
        # PDF 파일 추가
        files['pdf'] = (f'{paper_id}.pdf', pdf_content, 'application/pdf')
        logger.info(f"PDF 파일 크기: {len(pdf_content)} bytes")
        
        # AI 응답이 있으면 데이터에 추가
        if ai_response:
            logger.info("AI 응답 데이터 추가:")
            
            if 'summary' in ai_response:
                data['summary'] = ai_response['summary']
                logger.debug(f"  summary: {len(ai_response['summary'])} 문자")
            
            if 'translatedSummary' in ai_response:
                data['translatedSummary'] = ai_response['translatedSummary']
                logger.debug(f"  translatedSummary: {len(ai_response['translatedSummary'])} 문자")
            
            if 'content' in ai_response:
                data['content'] = ai_response['content']
                logger.debug(f"  content: {len(ai_response['content'])} 문자")
            
            if 'hashtags' in ai_response:
                data['hashtags'] = ai_response['hashtags']
                hashtag_count = len(json.loads(ai_response['hashtags']))
                logger.debug(f"  hashtags: {hashtag_count}개")
            
            if 'interestedUsers' in ai_response:
                data['interestedUsers'] = ai_response['interestedUsers']
                user_count = len(json.loads(ai_response['interestedUsers']))
                logger.debug(f"  interestedUsers: {user_count}명")
            
            if 'notifications' in ai_response:
                data['notifications'] = ai_response['notifications']
                notification_count = len(json.loads(ai_response['notifications']))
                logger.debug(f"  notifications: {notification_count}개")
            
            if 'thumbnail_bytes' in ai_response:
                files['thumbnail'] = ('thumbnail.png', ai_response['thumbnail_bytes'], 'image/png')
                logger.debug(f"  thumbnail: {len(ai_response['thumbnail_bytes'])} bytes (AI 생성)")
        else:
            logger.warning("AI 응답 없음")
        
        # AI 응답이 없으면 기본 썸네일 사용
        if 'thumbnail' not in files:
            thumbnail_content = load_thumbnail()
            if thumbnail_content:
                files['thumbnail'] = ('thumbnail.webp', thumbnail_content, 'image/webp')
                logger.debug(f"  thumbnail: {len(thumbnail_content)} bytes (기본 이미지)")
        
        logger.info(f"요청 URL: {PAPERS_CREATE_URL}")
        logger.info(f"타임아웃: {BACKEND_TIMEOUT}초")
        logger.info(f"전송 파일: {list(files.keys())}")
        logger.info(f"전송 데이터 필드: {list(data.keys())}")
        
        print("  → 백엔드 서버로 업로드 중...", end=" ", flush=True)
        
        request_start = time.time()
        response = requests.post(
            PAPERS_CREATE_URL,
            headers=headers,
            data=data,
            files=files,
            timeout=BACKEND_TIMEOUT
        )
        request_time = time.time() - request_start
        
        logger.info(f"응답 수신 완료 (소요 시간: {request_time:.2f}초)")
        logger.info(f"응답 상태 코드: {response.status_code}")
        
        if response.status_code == 200 or response.status_code == 201:
            logger.info("응답 내용 (성공):")
            try:
                response_data = response.json()
                log_dict(logger, response_data, "응답 데이터")
            except:
                logger.debug(f"응답 텍스트: {response.text[:200]}...")
            
            elapsed = time.time() - start_time
            logger.info(f"Backend Server (Upload) 총 소요 시간: {elapsed:.2f}초")
            logger.info("✓ 논문 업로드 완료")
            
            print("성공")
            return True
        else:
            logger.error(f"업로드 실패 - HTTP {response.status_code}")
            logger.error(f"응답 내용: {response.text[:500]}...")
            
            elapsed = time.time() - start_time
            logger.error(f"소요 시간: {elapsed:.2f}초")
            
            print(f"실패 (HTTP {response.status_code}: {response.text[:100]})")
            return False
            
    except requests.exceptions.Timeout as e:
        elapsed = time.time() - start_time
        logger.error(f"백엔드 서버 타임아웃 (소요 시간: {elapsed:.2f}초)")
        logger.error(f"타임아웃 설정: {BACKEND_TIMEOUT}초")
        print(f"실패 (타임아웃: {str(e)[:50]})")
        return False
    except requests.exceptions.RequestException as e:
        elapsed = time.time() - start_time
        logger.error(f"백엔드 서버 네트워크 오류 (소요 시간: {elapsed:.2f}초)")
        logger.error(f"오류: {str(e)}", exc_info=True)
        print(f"실패 (네트워크 오류: {str(e)[:50]})")
        return False
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"백엔드 서버 처리 중 오류 (소요 시간: {elapsed:.2f}초)")
        logger.error(f"오류: {str(e)}", exc_info=True)
        print(f"실패 (오류: {str(e)[:50]})")
        return False

