from fastapi import APIRouter

from app.api.routes import agent, health, llm

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(llm.router)
api_router.include_router(agent.router)
