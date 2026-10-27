from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"] = "user"
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1, description="对话消息列表")
    model: str | None = Field(None, description="覆盖默认模型名")
    temperature: float | None = Field(None, ge=0, le=2, description="覆盖默认温度")


class ChatResponse(BaseModel):
    model: str
    content: str = Field(..., description="模型回复内容")
