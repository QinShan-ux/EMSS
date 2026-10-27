from collections.abc import Iterator

from langchain_core.messages import AIMessage, BaseMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.schemas.llm import ChatRequest


class LLMNotConfiguredError(RuntimeError):
    """LLM_API_KEY 未配置时抛出。"""


def build_chat_model(model: str | None = None, temperature: float | None = None) -> ChatOpenAI:
    if not settings.llm_configured:
        raise LLMNotConfiguredError(
            "LLM_API_KEY 未配置，请在 .env 中设置 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL"
        )
    return ChatOpenAI(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        model=model or settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE if temperature is None else temperature,
        timeout=settings.LLM_TIMEOUT,
    )


def to_lc_messages(messages) -> list[BaseMessage]:
    """将 Pydantic ChatMessage 列表转换为 LangChain 消息。"""
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    mapping = {
        "system": SystemMessage,
        "user": HumanMessage,
        "assistant": AIMessage,
    }
    return [mapping[m.role](content=m.content) for m in messages]


class LLMService:
    """基于 LangChain ChatOpenAI 的 LLM 封装。"""

    def chat(self, request: ChatRequest) -> AIMessage:
        llm = build_chat_model(request.model, request.temperature)
        return llm.invoke(to_lc_messages(request.messages))

    def stream(self, request: ChatRequest) -> Iterator[str]:
        llm = build_chat_model(request.model, request.temperature)
        for chunk in llm.stream(to_lc_messages(request.messages)):
            if chunk.content:
                yield str(chunk.content)
