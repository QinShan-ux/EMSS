from functools import lru_cache

from fastapi import APIRouter

from app.api.errors import to_http_error
from app.schemas.agent import AgentRequest, AgentResponse
from app.services.agent_service import AgentService

router = APIRouter(prefix="/agent", tags=["agent"])


@lru_cache
def get_agent_service() -> AgentService:
    return AgentService()


@router.post("/run", response_model=AgentResponse)
async def run_agent(request: AgentRequest):
    """执行 Agent 任务：根据输入自主决定是否调用工具，返回最终答案与工具调用轨迹。"""
    try:
        return get_agent_service().run(request)
    except Exception as exc:
        raise to_http_error(exc) from exc
