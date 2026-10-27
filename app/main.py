from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.api.routes import api_router
from app.core.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行（如初始化数据库连接等）
    if not settings.llm_configured:
        logger.warning(
            "LLM_API_KEY 未配置！LLM/Agent 接口将返回 500，"
            "请复制 .env.example 为 .env 并填写 LLM 配置"
        )
    else:
        logger.info("LLM 已配置: model=%s, base_url=%s", settings.LLM_MODEL, settings.LLM_BASE_URL)
    yield
    # 关闭时执行（如释放资源等）


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

app.include_router(api_router, prefix=settings.API_PREFIX)
