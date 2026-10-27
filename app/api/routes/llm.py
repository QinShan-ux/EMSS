import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.errors import to_http_error
from app.schemas.llm import ChatRequest, ChatResponse
from app.services.llm_service import LLMService

router = APIRouter(prefix="/llm", tags=["llm"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """对话补全：发送消息列表，返回模型回复。"""
    try:
        result = LLMService().chat(request)
    except Exception as exc:
        raise to_http_error(exc) from exc
    return ChatResponse(model=result.response_metadata.get("model_name", request.model or ""), content=result.text)


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """对话补全（SSE 流式）：以 text/event-stream 增量返回内容，结束发送 [DONE]。"""
    try:
        iterator = LLMService().stream(request)
    except Exception as exc:
        raise to_http_error(exc) from exc

    def sse():
        for delta in iterator:
            yield f"data: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(sse(), media_type="text/event-stream")
