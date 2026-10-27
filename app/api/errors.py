from fastapi import HTTPException

from app.services.llm_service import LLMNotConfiguredError


def to_http_error(exc: Exception) -> HTTPException:
    """将 LLM/Agent 调用异常转换为结构化 HTTP 错误。"""
    if isinstance(exc, LLMNotConfiguredError):
        return HTTPException(status_code=500, detail=str(exc))
    return HTTPException(status_code=502, detail=f"LLM 服务调用失败: {exc}")
