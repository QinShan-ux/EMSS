from langchain.agents import create_agent

from app.schemas.agent import AgentRequest, AgentResponse, ToolCallRecord
from app.services.llm_service import build_chat_model, to_lc_messages
from app.tools.builtin import TOOLS


class AgentService:
    """基于 LangChain create_agent（LangGraph ReAct）的 Agent 封装，支持工具调用。"""

    def __init__(self):
        self._agent = create_agent(build_chat_model(), TOOLS)

    def run(self, request: AgentRequest) -> AgentResponse:
        messages = to_lc_messages(request.chat_history)
        messages.append(("user", request.input))

        result = self._agent.invoke({"messages": messages})

        tool_calls: list[ToolCallRecord] = []
        pending_ids: list[str] = []
        output_by_tool_call_id: dict[str, str] = {}
        answer = ""

        for msg in result["messages"]:
            if msg.type == "ai" and getattr(msg, "tool_calls", None):
                for tc in msg.tool_calls:
                    tool_calls.append(ToolCallRecord(tool=tc["name"], args=tc["args"]))
                    pending_ids.append(tc["id"])
            elif msg.type == "tool":
                output_by_tool_call_id[msg.tool_call_id] = str(msg.content)
            elif msg.type == "ai":
                answer = str(msg.content)

        for record, tc_id in zip(tool_calls, pending_ids):
            record.output = output_by_tool_call_id.get(tc_id)

        return AgentResponse(answer=answer, tool_calls=tool_calls)
