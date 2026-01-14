"""
채팅 API 라우터 (에이전트 기반)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.agent_service import agent_service
from services.supabase_client import supabase_service
from typing import List, Dict, Any, Optional

router = APIRouter()

# 세션별 대화 히스토리 (간단한 인메모리 저장)
# 실제 운영 환경에서는 Redis나 DB 사용 권장
conversation_sessions: Dict[str, List[Dict[str, Any]]] = {}


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"  # 세션 ID (프론트에서 생성)


class ChatResponse(BaseModel):
    response: str
    sources: List[str] = []
    source_urls: List[str] = []  # 다운로드 URL
    debug_logs: List[Dict[str, Any]] = []  # 디버깅 로그 (선택적)


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    에이전트 기반 채팅 메시지 처리

    - LLM이 대화 흐름을 주도
    - 필요할 때만 search_documents 도구 호출
    - 자연스러운 대화 + 출처 기반 팩트 혼합
    """
    try:
        session_id = request.session_id

        # 세션 히스토리 가져오기
        if session_id not in conversation_sessions:
            conversation_sessions[session_id] = []

        history = conversation_sessions[session_id]

        # 에이전트 대화 실행
        result = await agent_service.chat(
            user_message=request.message,
            history=history
        )

        # 히스토리 업데이트
        history.append({"role": "user", "parts": [request.message]})
        history.append({"role": "model", "parts": [result["response"]]})

        # 최근 10턴만 유지 (메모리 절약)
        if len(history) > 20:
            conversation_sessions[session_id] = history[-20:]

        # 채팅 로그 저장
        await supabase_service.insert_chat_log(
            request.message,
            result["response"],
            is_fact_mode=result["used_search"]
        )

        return ChatResponse(
            response=result["response"],
            sources=result["sources"],
            source_urls=result.get("source_urls", []),
            debug_logs=result.get("debug_logs", [])  # 디버그 로그 포함
        )

    except Exception as e:
        print(f"\n{'='*80}")
        print(f"❌ 채팅 오류: {e}")
        print(f"{'='*80}\n")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"채팅 처리 중 오류가 발생했습니다: {str(e)}")


@router.post("/reset")
async def reset_session(session_id: str = "default"):
    """대화 히스토리 초기화"""
    if session_id in conversation_sessions:
        del conversation_sessions[session_id]
    return {"status": "ok", "message": f"세션 {session_id} 초기화 완료"}
