import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections per session for real-time diagram updates."""

    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self._connections.setdefault(session_id, []).append(websocket)
        logger.info(f"WebSocket connected for session {session_id}")

    async def disconnect(self, session_id: str, websocket: WebSocket):
        conns = self._connections.get(session_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self._connections.pop(session_id, None)
        logger.info(f"WebSocket disconnected for session {session_id}")

    async def broadcast(self, session_id: str, event: dict[str, Any]):
        """Send diagram update event to all clients watching this session."""
        dead = []
        for ws in self._connections.get(session_id, []):
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(session_id, ws)

    def has_connections(self, session_id: str) -> bool:
        return bool(self._connections.get(session_id))


ws_manager = WebSocketManager()
