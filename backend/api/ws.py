import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.services.ws_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time diagram updates."""
    await ws_manager.connect(session_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # Handle client events
            event_type = data.get("type")
            if event_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif event_type == "request_sync":
                # Client requests full diagram sync
                # This would normally fetch and send full state
                await websocket.send_json(
                    {"type": "sync_requested", "session_id": session_id}
                )
    except WebSocketDisconnect:
        await ws_manager.disconnect(session_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        await ws_manager.disconnect(session_id, websocket)
