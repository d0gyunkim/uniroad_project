"""
UniZ 통합 테스트 서버
Orchestration Agent + Sub Agent + Final Pipeline 통합
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
from pathlib import Path
from dotenv import load_dotenv
import sys

# 경로 설정
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir.parent))

# .env 로드
env_path = current_dir.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ .env 파일 로드됨: {env_path}")

# Multi-Agent 시스템 import
from services.multi_agent.orchestration_agent import run_orchestration_agent
from services.multi_agent.sub_agents import ConsultingAgent, get_agent
import asyncio

app = FastAPI(title="UniZ 통합 테스트 서버")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class OrchestrationRequest(BaseModel):
    message: str


class SubAgentRequest(BaseModel):
    agent_type: str  # "university", "consulting", "teacher"
    university_name: Optional[str] = None
    query: str


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


# =============================================================================
# 1. Orchestration Agent API
# =============================================================================
@app.post("/api/orchestration")
async def test_orchestration(request: OrchestrationRequest):
    """Orchestration Agent만 실행"""
    try:
        result = await run_orchestration_agent(request.message)
        return result
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "detail": traceback.format_exc()
        }


# =============================================================================
# 2. Sub Agent API
# =============================================================================
@app.post("/api/subagent")
async def test_subagent(request: SubAgentRequest):
    """Sub Agent 단독 실행"""
    try:
        # Agent 선택
        if request.agent_type == "university":
            if not request.university_name:
                raise HTTPException(status_code=400, detail="university_name is required")
            agent = get_agent(f"{request.university_name} agent")
        elif request.agent_type == "consulting":
            agent = ConsultingAgent()
        elif request.agent_type == "teacher":
            agent = get_agent("선생님 agent")
        else:
            raise HTTPException(status_code=400, detail=f"Invalid agent_type: {request.agent_type}")
        
        # Agent 실행
        result = await agent.execute(request.query)
        
        return {
            "agent_name": agent.name,
            "status": result.get("status", "unknown"),
            "result": result.get("result", "No result"),
            "normalized_scores": result.get("normalized_scores"),
            "sources": result.get("sources"),
            "source_urls": result.get("source_urls")
        }
        
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "detail": traceback.format_exc()
        }


# =============================================================================
# 3. 전체 파이프라인 API
# =============================================================================
conversation_history: Dict[str, list] = {}


@app.post("/api/chat")
async def full_pipeline(request: ChatRequest):
    """
    전체 파이프라인 실행:
    1. Orchestration Agent → Execution Plan
    2. Sub Agents 실행
    3. Final Agent → 최종 답변
    """
    try:
        # 세션 초기화
        if request.session_id not in conversation_history:
            conversation_history[request.session_id] = []
        
        # 1. Orchestration Agent
        orchestration_result = await run_orchestration_agent(request.message)
        
        if "error" in orchestration_result:
            return {
                "stage": "orchestration",
                "error": orchestration_result["error"],
                "orchestration_result": orchestration_result
            }
        
        execution_plan = orchestration_result.get("execution_plan", [])
        answer_structure = orchestration_result.get("answer_structure", [])
        
        # 2. Sub Agents 실행
        from services.multi_agent.sub_agents import execute_sub_agents
        sub_agent_results = await execute_sub_agents(execution_plan)
        
        # 3. Final Agent
        from services.multi_agent.final_agent import generate_final_answer
        final_result = await generate_final_answer(
            user_question=request.message,
            answer_structure=answer_structure,
            sub_agent_results=sub_agent_results,
            notes=orchestration_result.get("notes", "")
        )
        
        final_answer = final_result.get("final_answer", "답변 생성 실패")
        
        # 대화 이력 추가
        conversation_history[request.session_id].append({
            "role": "user",
            "content": request.message
        })
        conversation_history[request.session_id].append({
            "role": "assistant",
            "content": final_answer
        })
        
        return {
            "stage": "complete",
            "orchestration_result": orchestration_result,
            "sub_agent_results": sub_agent_results,
            "final_answer": final_answer,
            "metadata": final_result.get("metadata", {})
        }
        
    except Exception as e:
        import traceback
        return {
            "stage": "error",
            "error": str(e),
            "detail": traceback.format_exc()
        }


# =============================================================================
# 프론트엔드 서빙
# =============================================================================
@app.get("/")
async def serve_frontend():
    """프론트엔드 HTML 서빙"""
    html_path = current_dir / "test_unified_web.html"
    if html_path.exists():
        return FileResponse(html_path)
    else:
        return {"message": "Frontend not found. Please create test_unified_web.html"}


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "ok", "message": "UniZ 통합 테스트 서버 정상 작동 중"}


if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*70)
    print("🚀 UniZ 통합 테스트 서버")
    print("="*70)
    print("📍 Server: http://localhost:8095")
    print("📍 Frontend: http://localhost:8095/")
    print("="*70)
    print("\n포함된 테스트:")
    print("  1. 🎯 Orchestration Agent (질문 분석 & 계획 수립)")
    print("  2. 📊 Sub Agent (개별 Agent 테스트)")
    print("  3. 🚀 Final Pipeline (전체 파이프라인)")
    print("\n상단 탭을 클릭해서 전환하세요!\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8095)
