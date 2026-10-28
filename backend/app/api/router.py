from fastapi import APIRouter

from app.api.v1 import agents, graph, health, mlops, rag, repositories

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(repositories.router)
api_router.include_router(graph.router)
api_router.include_router(agents.router)
api_router.include_router(rag.router)
api_router.include_router(mlops.router)
