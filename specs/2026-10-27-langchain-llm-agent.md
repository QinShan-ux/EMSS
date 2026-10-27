# Spec: LangChain 基于 OpenAPI 风格封装 LLM 和 Agent

日期：2026-10-27

## 需求概述

本次迭代在现有 FastAPI 项目中集成 LangChain，将 LLM 对话与 Agent（带工具调用能力）封装为符合 OpenAPI 规范的 REST 接口。通过 FastAPI 自动生成的 Swagger 文档（/docs）即可查看和调试所有 LLM/Agent 接口，为后续业务模块（EMSS）提供统一的 AI 能力入口。

## 功能点清单

- [x] F1: 集成 LangChain 依赖（langchain、langchain-openai，兼容 OpenAI 协议的任意模型服务如 DeepSeek/Qwen）
- [x] F2: 配置扩展 — `app/core/config.py` 增加 LLM 相关配置（API Key、Base URL、模型名、温度、超时），支持 `.env` 注入
- [x] F3: LLM 服务层 — `app/services/llm_service.py` 封装 LangChain ChatOpenAI，提供同步调用与流式输出
- [x] F4: LLM REST 接口 — `POST /api/v1/llm/chat`（对话补全）、`POST /api/v1/llm/chat/stream`（SSE 流式输出），请求/响应使用 Pydantic 模型并在 OpenAPI 文档中可见
- [x] F5: 工具定义 — `app/tools/` 下定义示例工具（如获取当前时间），可扩展
- [x] F6: Agent 服务层 — `app/services/agent_service.py` 基于 LangChain Agent（create_agent / ToolNode）封装，支持工具调用
- [x] F7: Agent REST 接口 — `POST /api/v1/agent/run`（执行 Agent 任务），返回最终答案与工具调用轨迹
- [x] F8: 统一错误处理 — LLM 调用失败（超时、鉴权失败、限流）返回结构化错误响应

## 影响范围

- `requirements.txt` — 新增 langchain 相关依赖
- `app/core/config.py` — 新增 LLM 配置项
- `app/api/routes/__init__.py` — 注册新路由
- 新增：`app/api/routes/llm.py`、`app/api/routes/agent.py`
- 新增：`app/services/llm_service.py`、`app/services/agent_service.py`
- 新增：`app/schemas/llm.py`、`app/schemas/agent.py`（Pydantic 请求/响应模型）
- 新增：`app/tools/`（示例工具目录）
- 新增：`.env.example`（LLM 配置模板）
- `app/main.py` — 无需改动（路由自动挂载）

## 验收标准

- F1: `pip install -r requirements.txt` 后 `import langchain` 成功
- F2: 在 `.env` 中配置 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL` 后服务可读取；未配置时启动给出清晰报错
- F3: 服务层可通过单元方式调用并返回文本结果
- F4: 访问 `/docs` 可见 `llm` 分组下的两个接口；`POST /llm/chat` 返回 JSON 响应；`/llm/chat/stream` 以 `text/event-stream` 返回增量内容
- F5: 示例工具可被 Agent 正确发现和调用
- F6: Agent 能根据用户输入自主决定是否调用工具并产出最终答案
- F7: 访问 `/docs` 可见 `agent` 分组接口；响应包含 `answer` 与 `tool_calls` 轨迹字段
- F8: LLM 服务异常时接口返回 502/500 + 结构化错误体（`{"detail": ...}`），不抛出裸异常

## 技术方案

- **模型接入**：使用 `langchain-openai` 的 `ChatOpenAI`，通过 `base_url` 指向任意 OpenAI 兼容服务（OpenAI / DeepSeek / 通义千问 / 本地 vLLM 等），一套代码适配多厂商
- **Agent 实现**：采用 LangChain v0.3+ 推荐的 `langgraph.prebuilt.create_react_agent`，稳定且支持工具调用轨迹回传
- **流式输出**：使用 FastAPI `StreamingResponse` + SSE 格式（`data: {...}\n\n`），前端可直接用 EventSource/fetch 消费
- **分层结构**：routes（HTTP 层）→ services（LangChain 封装层）→ schemas（契约层），业务后续可直接复用 services
- **依赖变更**：`langchain>=0.3`、`langchain-openai>=0.2`、`langgraph>=0.2`
- **风险点**：
  - Agent 工具调用依赖模型本身的 function-calling 能力，弱模型可能不触发工具
  - 流式接口在部分代理/网关下需关闭缓冲
  - API Key 泄露风险，通过 `.env` 管理并加入 `.gitignore`
