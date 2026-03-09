from fastapi import APIRouter

from backend.api.sessions import router as sessions_router
from backend.api.conversations import router as conversations_router
from backend.api.diagrams import router as diagrams_router
from backend.api.modes import router as modes_router
from backend.api.ws import router as ws_router

api_router = APIRouter()
api_router.include_router(modes_router, prefix="/modes", tags=["modes"])
api_router.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
api_router.include_router(
    conversations_router, prefix="/sessions", tags=["conversations"]
)
api_router.include_router(diagrams_router, prefix="/sessions", tags=["diagrams"])
api_router.include_router(ws_router, tags=["websocket"])
