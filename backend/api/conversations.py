from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.schemas.message import (
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)
from backend.services.conversation_engine import conversation_engine
from backend.services.session_manager import session_manager

router = APIRouter()


@router.post("/{session_id}/messages")
async def send_message(
    session_id: str,
    body: MessageCreate,
    db: AsyncSession = Depends(get_db),
):
    """Send a user message and get AI response with diagram updates."""
    session = await session_manager.get(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "active":
        raise HTTPException(
            status_code=400, detail="Session is not active"
        )

    result = await conversation_engine.process_message(
        db, session_id, body.content
    )
    return result.model_dump(mode="json")


@router.get(
    "/{session_id}/messages", response_model=list[MessageResponse]
)
async def get_messages(
    session_id: str, db: AsyncSession = Depends(get_db)
):
    """Get conversation history for a session."""
    session = await session_manager.get(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = await session_manager.get_messages(db, session_id)
    return [MessageResponse.model_validate(m) for m in messages]
