from pydantic import BaseModel, Field

from app.schemas.llm import ChatMessage


class ToolCallRecord(BaseModel):
    tool: str = Field(..., description="工具名称")
    args: dict = Field(default_factory=dict, description="工具调用参数")
    output: str | None = Field(None, description="工具执行结果")


class AgentRequest(BaseModel):
    input: str = Field(..., min_length=1, description="用户任务描述")
    chat_history: list[ChatMessage] = Field(default_factory=list, description="历史对话")


class AgentResponse(BaseModel):
    answer: str = Field(..., description="Agent 最终回答")
    tool_calls: list[ToolCallRecord] = Field(default_factory=list, description="工具调用轨迹")
