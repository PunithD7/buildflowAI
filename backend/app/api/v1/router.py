"""
API v1 Main Router
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    projects,
    workflows,
    agents,
    observability,
    security,
    documents,
    artifacts,
    # websocket is mounted directly on the app (not under /api/v1 prefix)
    # because the frontend connects to ws://host/ws/{id}, not ws://host/api/v1/ws/{id}
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["Workflows"])
api_router.include_router(agents.router, prefix="/agents", tags=["Agents"])
api_router.include_router(observability.router, prefix="/observability", tags=["Observability"])
api_router.include_router(security.router, prefix="/security", tags=["Security"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(artifacts.router, prefix="/artifacts", tags=["Artifacts"])
# NOTE: WebSocket router is NOT included here — it must be mounted at root level
# in main.py because the frontend connects to ws://host/ws/{id}, not /api/v1/ws/{id}

