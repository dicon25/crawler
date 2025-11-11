"""
AI 서버 통신 모듈
"""

import base64
import json
import time
from typing import Dict, List, Optional

import requests

from config import AI_SERVER_TIMEOUT, AI_SUMMARIZE_URL
from logger import log_dict, setup_logger
from models import ProcessedAIResponse

logger = setup_logger("ai_service")


def process_ai_response(ai_response: Dict) -> ProcessedAIResponse:
    """
    AI 서버 응답을 백엔드에 전송할 형식으로 처리
    
    Args:
        ai_response: AI 서버 응답
    
    Returns:
        처리된 데이터 딕셔너리
    """
    processed = {}
    
    logger.debug("=" * 80)
    logger.debug("AI 응답 처리 시작")
    logger.debug(f"AI 응답 키: {list(ai_response.keys())}")
    
    # 1. summary와 translatedSummary 추가
    if 'summary' in ai_response:
        processed['summary'] = ai_response['summary']
        logger.debug(f"summary 추가: {len(ai_response['summary'])} 문자")
    else:
        logger.warning("AI 응답에 'summary' 없음")
    
    if 'translatedSummary' in ai_response:
        processed['translatedSummary'] = ai_response['translatedSummary']
        logger.debug(f"translatedSummary 추가: {len(ai_response['translatedSummary'])} 문자")
    else:
        logger.warning("AI 응답에 'translatedSummary' 없음")
    
    # 2. tableOfContents와 contents를 content 필드로 통합
    content_data = {}
    
    if 'tableOfContents' in ai_response and ai_response['tableOfContents']:
        content_data['tableOfContents'] = ai_response['tableOfContents']
        logger.debug(f"tableOfContents 추가: {len(ai_response['tableOfContents'])}개 항목")
    else:
        logger.warning("AI 응답에 'tableOfContents' 없음 또는 비어있음")
        content_data['tableOfContents'] = []
    
    if 'contents' in ai_response and ai_response['contents']:
        content_data['contents'] = ai_response['contents']
        logger.debug(f"contents 추가: {len(ai_response['contents'])}개 항목")
    else:
        logger.warning("AI 응답에 'contents' 없음 또는 비어있음")
        content_data['contents'] = []
    
    # content는 항상 생성 (백엔드 필수 필드)
    processed['content'] = json.dumps(content_data, ensure_ascii=False)
    logger.debug(f"content JSON 생성: {len(processed['content'])} 문자")
    logger.debug(f"content 미리보기: {processed['content'][:200]}...")
    
    # 3. hashtags 추가
    if 'hashtags' in ai_response and ai_response['hashtags']:
        processed['hashtags'] = json.dumps(ai_response['hashtags'], ensure_ascii=False)
        logger.debug(f"hashtags 추가: {len(ai_response['hashtags'])}개")
    else:
        logger.warning("AI 응답에 'hashtags' 없음 또는 비어있음")
    
    # 4. interestedUsers에서 userId만 추출하여 배열로 변환
    if 'interestedUsers' in ai_response and isinstance(ai_response['interestedUsers'], list):
        interested_user_ids = [user['userId'] for user in ai_response['interestedUsers'] if 'userId' in user]
        processed['interestedUsers'] = json.dumps(interested_user_ids, ensure_ascii=False)
        logger.debug(f"interestedUsers 추가: {len(interested_user_ids)}명")
    else:
        logger.warning("AI 응답에 'interestedUsers' 없음 또는 비어있음")
    
    # 5. notifications 추가 (JSON 그대로 전달)
    if 'notifications' in ai_response and ai_response['notifications']:
        processed['notifications'] = json.dumps(ai_response['notifications'], ensure_ascii=False)
        notification_count = len(ai_response['notifications']) if isinstance(ai_response['notifications'], list) else 1
        logger.debug(f"notifications 추가: {notification_count}개")
        logger.debug(f"notifications 미리보기: {str(ai_response['notifications'])[:200]}...")
    else:
        logger.warning("AI 응답에 'notifications' 없음 또는 비어있음")
    
    # 6. thumbnail은 base64이므로 별도 처리 (bytes로 변환)
    if 'thumbnail' in ai_response and ai_response['thumbnail']:
        try:
            # base64 디코드
            thumbnail_bytes = base64.b64decode(ai_response['thumbnail'])
            processed['thumbnail_bytes'] = thumbnail_bytes
            logger.debug(f"thumbnail 디코딩 완료: {len(thumbnail_bytes)} bytes")
        except Exception as e:
            logger.error(f"썸네일 디코딩 실패: {str(e)}", exc_info=True)
            print(f"    ⚠ 경고: 썸네일 디코딩 실패: {str(e)[:50]}")
    else:
        logger.warning("AI 응답에 'thumbnail' 없음 또는 비어있음")
    
    logger.debug("AI 응답 처리 완료")
    logger.debug(f"처리된 키: {list(processed.keys())}")
    logger.debug("=" * 80)
    
    return processed


def summarize_paper_with_ai(pdf_content: bytes, activities: List[Dict], paper_id: str) -> Optional[ProcessedAIResponse]:
    """
    AI 서버로 PDF와 활동 정보를 전송하여 논문 요약 받기
    
    Args:
        pdf_content: PDF 파일의 바이너리 데이터
        activities: 사용자 활동 정보 목록
        paper_id: 논문 ID
    
    Returns:
        처리된 AI 서버 응답 (딕셔너리) 또는 None
    """
    start_time = time.time()
    logger.info("=" * 80)
    logger.info("AI Server: 논문 요약 요청 시작")
    logger.info("=" * 80)
    
    try:
        # 요청 데이터 로깅
        logger.info(f"Paper ID: {paper_id}")
        logger.info(f"PDF 크기: {len(pdf_content)} bytes")
        
        # activities의 타입에 따라 처리
        if isinstance(activities, list):
            logger.info(f"사용자 활동 정보 개수: {len(activities)}")
            logger.debug(f"사용자 활동 정보:")
            for idx, activity in enumerate(activities[:3]):  # 처음 3개만
                logger.debug(f"  Activity {idx + 1}: {activity}")
        elif isinstance(activities, dict):
            logger.info(f"사용자 활동 정보 타입: dict")
            logger.debug(f"사용자 활동 정보: {activities}")
        else:
            logger.info(f"사용자 활동 정보: {activities}")
        
        # multipart/form-data로 전송
        files = {
            'file': (f'{paper_id}.pdf', pdf_content, 'application/pdf')
        }
        
        data = {
            'id': paper_id,  # Paper ID 추가 (예: arxiv:2401.12345v1)
            'activity': json.dumps(activities)
        }
        
        logger.info(f"AI 서버 URL: {AI_SUMMARIZE_URL}")
        logger.info(f"타임아웃: {AI_SERVER_TIMEOUT}초")
        logger.debug(f"전송 데이터:")
        logger.debug(f"  id: {paper_id}")
        logger.debug(f"  activity: {len(json.dumps(activities))} 문자")
        logger.debug(f"  file: {paper_id}.pdf ({len(pdf_content)} bytes)")
        
        print("  → AI 서버로 요약 요청 중...", end=" ", flush=True)
        
        request_start = time.time()
        response = requests.post(
            AI_SUMMARIZE_URL,
            files=files,
            data=data,
            timeout=AI_SERVER_TIMEOUT
        )
        request_time = time.time() - request_start
        
        logger.info(f"AI 서버 응답 수신 완료 (소요 시간: {request_time:.2f}초)")
        logger.info(f"응답 상태 코드: {response.status_code}")
        logger.info(f"응답 크기: {len(response.content)} bytes")
        
        response.raise_for_status()
        
        # 원본 응답 출력
        logger.info("=" * 80)
        logger.info("AI 서버 원본 응답:")
        logger.info(response.text)
        logger.info("=" * 80)
        
        ai_response = response.json()
        logger.debug(f"응답 키: {list(ai_response.keys())}")
        
        print("성공")
        print(f"  → AI 서버 응답: {response.text[:200]}..." if len(response.text) > 200 else f"  → AI 서버 응답: {response.text}")
        
        # AI 응답 상세 로깅
        if 'summary' in ai_response:
            logger.info(f"Summary 길이: {len(ai_response['summary'])} 문자")
            logger.debug(f"Summary 미리보기: {ai_response['summary'][:200]}...")
        
        if 'translatedSummary' in ai_response:
            logger.info(f"Translated Summary 길이: {len(ai_response['translatedSummary'])} 문자")
            logger.debug(f"Translated Summary 미리보기: {ai_response['translatedSummary'][:200]}...")
        
        if 'tableOfContents' in ai_response:
            logger.info(f"Table of Contents: {len(ai_response['tableOfContents'])}개 항목")
        
        if 'contents' in ai_response:
            logger.info(f"Contents: {len(ai_response['contents'])}개 항목")
        
        if 'hashtags' in ai_response:
            logger.info(f"Hashtags: {len(ai_response['hashtags'])}개")
            logger.debug(f"Hashtags: {[h.get('tag', '') for h in ai_response['hashtags'][:5]]}")
        
        if 'interestedUsers' in ai_response:
            logger.info(f"Interested Users: {len(ai_response['interestedUsers'])}명")
            user_ids = [u.get('userId', '') for u in ai_response['interestedUsers'][:5]]
            logger.debug(f"User IDs (처음 5개): {user_ids}")
        
        if 'notifications' in ai_response:
            notification_count = len(ai_response['notifications']) if isinstance(ai_response['notifications'], list) else 1
            logger.info(f"Notifications: {notification_count}개")
            logger.debug(f"Notifications 미리보기: {str(ai_response['notifications'])[:200]}...")
        
        if 'thumbnail' in ai_response:
            thumbnail_len = len(ai_response['thumbnail']) if ai_response['thumbnail'] else 0
            logger.info(f"Thumbnail (base64) 길이: {thumbnail_len} 문자")
        
        # AI 응답 처리
        processed_response = process_ai_response(ai_response)
        
        # 응답 요약 출력
        summary_info = {
            'has_summary': 'summary' in processed_response,
            'has_translatedSummary': 'translatedSummary' in processed_response,
            'has_content': 'content' in processed_response,
            'has_hashtags': 'hashtags' in processed_response,
            'has_thumbnail': 'thumbnail_bytes' in processed_response,
            'interested_users_count': len(json.loads(processed_response.get('interestedUsers', '[]'))),
            'notifications_count': len(json.loads(processed_response.get('notifications', '[]'))) if 'notifications' in processed_response else 0
        }
        print(f"  → AI 응답 처리 완료: {json.dumps(summary_info, ensure_ascii=False)}")
        logger.info(f"응답 처리 완료: {summary_info}")
        
        elapsed = time.time() - start_time
        logger.info(f"AI Server 총 소요 시간: {elapsed:.2f}초")
        logger.info("✓ AI 서버 요약 완료")
        
        return processed_response
        
    except requests.exceptions.Timeout as e:
        elapsed = time.time() - start_time
        logger.error(f"AI 서버 타임아웃 (소요 시간: {elapsed:.2f}초)")
        logger.error(f"타임아웃 설정: {AI_SERVER_TIMEOUT}초")
        print(f"실패 (타임아웃: {str(e)[:100]})")
        return None
    except requests.exceptions.RequestException as e:
        elapsed = time.time() - start_time
        logger.error(f"AI 서버 네트워크 오류 (소요 시간: {elapsed:.2f}초)")
        logger.error(f"오류: {str(e)}", exc_info=True)
        print(f"실패 (네트워크 오류: {str(e)[:100]})")
        return None
    except json.JSONDecodeError as e:
        elapsed = time.time() - start_time
        logger.error(f"AI 서버 응답 파싱 오류 (소요 시간: {elapsed:.2f}초)")
        logger.error(f"응답 내용: {response.text[:500]}...")
        logger.error(f"오류: {str(e)}", exc_info=True)
        print(f"실패 (응답 파싱 오류: {str(e)[:100]})")
        return None
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"AI 서버 처리 중 오류 (소요 시간: {elapsed:.2f}초)")
        logger.error(f"오류: {str(e)}", exc_info=True)
        print(f"실패 (오류: {str(e)[:100]})")
        return None

