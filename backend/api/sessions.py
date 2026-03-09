from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.schemas.session import (
    SessionCreate,
    SessionListResponse,
    SessionResponse,
    SessionUpdate,
)
from backend.services.conversation_engine import conversation_engine
from backend.services.mode_registry import get_mode
from backend.services.session_manager import session_manager

router = APIRouter()


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    body: SessionCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new consultation session."""
    # Validate mode exists
    try:
        get_mode(body.mode_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown mode: {body.mode_id}")

    session = await session_manager.create(db, body.mode_id, body.title)
    return SessionResponse.model_validate(session)


@router.get("", response_model=SessionListResponse)
async def list_sessions(db: AsyncSession = Depends(get_db)):
    """List all saved sessions."""
    sessions = await session_manager.list_all(db)
    return SessionListResponse(
        sessions=[SessionResponse.model_validate(s) for s in sessions]
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get session details."""
    session = await session_manager.get(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse.model_validate(session)


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    body: SessionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update session (rename, pause, etc.)."""
    session = await session_manager.update(
        db, session_id, title=body.title, status=body.status
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse.model_validate(session)


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: str, db: AsyncSession = Depends(get_db)
):
    """Delete a session and all its data."""
    deleted = await session_manager.delete(db, session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")


@router.post("/{session_id}/start")
async def start_session(
    session_id: str, db: AsyncSession = Depends(get_db)
):
    """Start the AI consultation for a newly created session."""
    session = await session_manager.get(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    result = await conversation_engine.start_session(db, session_id)
    return result.model_dump(mode="json")


@router.post("/{session_id}/resume")
async def resume_session(
    session_id: str, db: AsyncSession = Depends(get_db)
):
    """Resume a paused session."""
    session = await session_manager.get(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "paused":
        raise HTTPException(
            status_code=400, detail="Session is not paused"
        )

    result = await conversation_engine.resume_session(db, session_id)
    return result.model_dump(mode="json")
