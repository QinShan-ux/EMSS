"""端到端验证脚本：使用本地 mock OpenAI 服务测试 LLM/Agent 接口。

运行：python tests/test_llm_endpoints.py
"""

import json
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

# 1. 先设置 LLM 环境变量（config 在导入时加载）
import os

os.environ["LLM_API_KEY"] = "test-key"
os.environ["LLM_BASE_URL"] = "http://127.0.0.1:8124/v1"
os.environ["LLM_MODEL"] = "mock-model"

# 2. mock OpenAI 兼容服务
mock = FastAPI()

FINAL_CONTENT = "现在时间是 12:00:00"
CHAT_CONTENT = "mock reply"


def completion_body(message: dict, finish_reason: str = "stop") -> dict:
    return {
        "id": "chatcmpl-mock",
        "object": "chat.completion",
        "created": 1,
        "model": "mock-model",
        "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }


@mock.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()

    # 流式请求
    if body.get("stream"):
        async def sse():
            chunks = [{"role": "assistant"}, {"content": "mock "}, {"content": "stream"}]
            for delta in chunks:
                yield "data: " + json.dumps({
                    "id": "chatcmpl-mock",
                    "object": "chat.completion.chunk",
                    "created": 1,
                    "model": "mock-model",
                    "choices": [{"index": 0, "delta": delta, "finish_reason": None}],
                }) + "\n\n"
            yield "data: " + json.dumps({
                "id": "chatcmpl-mock",
                "object": "chat.completion.chunk",
                "created": 1,
                "model": "mock-model",
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }) + "\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(sse(), media_type="text/event-stream")

    # Agent 流程：有 tools 时第一轮返回 tool_calls，第二轮（含 tool 消息）返回最终答案
    if body.get("tools"):
        has_tool_result = any(m.get("role") == "tool" for m in body["messages"])
        if has_tool_result:
            message = {"role": "assistant", "content": FINAL_CONTENT}
        else:
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "call_mock_1",
                    "type": "function",
                    "function": {"name": "get_current_time", "arguments": "{}"},
                }],
            }
        return completion_body(message)

    # 普通对话
    return completion_body({"role": "assistant", "content": CHAT_CONTENT})


def start_mock():
    config = uvicorn.Config(mock, host="127.0.0.1", port=8124, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.1)
    return server


# 3. 启动 mock 后导入被测应用
start_mock()
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)
passed, failed = 0, 0


def check(name: str, cond: bool, extra: str = ""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS {name}")
    else:
        failed += 1
        print(f"  FAIL {name} {extra}")


# --- 测试 llm/chat ---
print("[llm/chat]")
r = client.post("/api/v1/llm/chat", json={"messages": [{"role": "user", "content": "hi"}]})
check("status=200", r.status_code == 200, r.text)
data = r.json()
check("content", data.get("content") == CHAT_CONTENT, str(data))
check("model", data.get("model") == "mock-model", str(data))

r = client.post("/api/v1/llm/chat", json={"messages": []})
check("空消息列表返回422", r.status_code == 422, r.text)

# --- 测试 llm/chat/stream ---
print("[llm/chat/stream]")
r = client.post("/api/v1/llm/chat/stream", json={"messages": [{"role": "user", "content": "hi"}]})
check("status=200", r.status_code == 200, r.text)
check("content-type=text/event-stream", r.headers["content-type"].startswith("text/event-stream"))
deltas = [json.loads(line[6:]) for line in r.text.splitlines() if line.startswith("data: {")]
check("增量内容拼接", "".join(d.get("delta", "") for d in deltas) == "mock stream", r.text)
check("结束标记[DONE]", "[DONE]" in r.text)

# --- 测试 agent/run ---
print("[agent/run]")
r = client.post("/api/v1/agent/run", json={"input": "现在几点了？"})
check("status=200", r.status_code == 200, r.text)
data = r.json()
check("answer", data.get("answer") == FINAL_CONTENT, str(data))
tcs = data.get("tool_calls", [])
check("工具调用轨迹", len(tcs) == 1 and tcs[0]["tool"] == "get_current_time", str(data))
check("工具输出回填", tcs and tcs[0]["output"] is not None, str(data))

# --- 未配置 API Key 的错误处理 ---
print("[error handling]")
import subprocess
import sys

code = (
    "from fastapi.testclient import TestClient;"
    "from app.main import app;"
    "c = TestClient(app);"
    "r = c.post('/api/v1/llm/chat', json={'messages': [{'role': 'user', 'content': 'hi'}]});"
    "print(r.status_code, r.json())"
)
env = dict(os.environ)
env["LLM_API_KEY"] = ""  # load_dotenv 不覆盖已有变量，显式置空以模拟未配置
env["PYTHONIOENCODING"] = "utf-8"
out = subprocess.run(
    [sys.executable, "-c", code],
    capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=".", env=env,
)
check("未配置Key返回500", out.stdout.startswith("500"), out.stdout + out.stderr)
check("结构化错误信息", "LLM_API_KEY" in out.stdout, out.stdout)

print(f"\n结果: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
