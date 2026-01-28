"""
Multi-Agent Pipeline v2
Router → Functions → Main Agent 구조
- backend/services/multi_agent/ 로 통합됨
"""

import json
from typing import Dict, Any, List

from .router_agent import RouterAgent, route_query
from .admin_agent import AdminAgent, evaluate_router_output

# 기존 chat.py 호환용
AVAILABLE_AGENTS = [
    {"name": "router_agent", "description": "질문을 분석하여 적절한 함수 호출을 결정하는 에이전트"}
]


async def run_orchestration_agent(message: str, history: List[Dict] = None, timing_logger=None) -> Dict[str, Any]:
    """
    Orchestration Agent 실행 (router_agent 래퍼)
    - 기존 chat.py 호환 유지
    - router_agent의 출력을 direct_response로 전달
    """
    try:
        # router_agent 호출
        result = await route_query(message, history)
        
        # function_calls 추출
        function_calls = result.get("function_calls", [])
        
        # JSON 포맷팅
        formatted_output = json.dumps({"function_calls": function_calls}, ensure_ascii=False, indent=2)
        
        # 에러가 있으면 추가
        if "error" in result:
            formatted_output = f"오류: {result['error']}\n\n{formatted_output}"
        
        return {
            "user_intent": "router_agent 테스트",
            "execution_plan": [],
            "answer_structure": [],
            "direct_response": formatted_output,
            "extracted_scores": {},
            "router_result": result  # 원본 결과도 포함
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "user_intent": "오류 발생",
            "execution_plan": [],
            "answer_structure": [],
            "direct_response": f"Router Agent 오류: {str(e)}"
        }


async def execute_sub_agents(execution_plan, context, timing_logger=None) -> Dict[str, Any]:
    """Sub Agents 실행 (router_agent 모드에서는 사용하지 않음)"""
    return {}


async def generate_final_answer(
    message: str,
    orchestration_result: Dict,
    sub_agent_results: Dict,
    history: List[Dict] = None,
    timing_logger=None
) -> Dict[str, Any]:
    """Final Answer 생성 (router_agent 모드에서는 direct_response 사용)"""
    return {
        "final_answer": "",
        "raw_answer": "",
        "sources": [],
        "source_urls": [],
        "used_chunks": [],
        "metadata": {}
    }


def get_agent(name: str):
    """에이전트 가져오기"""
    return None


# ============================================================
# 더미 모듈 객체 (chat.py 호환용)
# - chat.py에서 orchestration_agent.set_log_callback() 등 호출
# - router_agent 모드에서는 실제로 사용하지 않음
# ============================================================
class _DummyModule:
    """set_log_callback 호출을 무시하는 더미 모듈"""
    def set_log_callback(self, callback):
        pass

orchestration_agent = _DummyModule()
sub_agents = _DummyModule()
final_agent = _DummyModule()


__all__ = [
    "RouterAgent",
    "route_query",
    "AdminAgent",
    "evaluate_router_output",
    "AVAILABLE_AGENTS",
    "run_orchestration_agent",
    "execute_sub_agents",
    "generate_final_answer",
    "get_agent",
    "orchestration_agent",
    "sub_agents",
    "final_agent",
]
