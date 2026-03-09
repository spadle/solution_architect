from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.schemas.diagram import DiagramState, ExportRequest, MermaidResponse
from backend.services.diagram_engine import diagram_engine
from backend.services.session_manager import session_manager

router = APIRouter()


@router.get("/{session_id}/diagram", response_model=DiagramState)
async def get_diagram(
    session_id: str, db: AsyncSession = Depends(get_db)
):
    """Get the full diagram state for a session."""
    session = await session_manager.get(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return await diagram_engine.get_full_state(db, session_id)


@router.get("/{session_id}/diagram/mermaid", response_model=MermaidResponse)
async def get_mermaid(
    session_id: str, db: AsyncSession = Depends(get_db)
):
    """Get the diagram as Mermaid syntax."""
    session = await session_manager.get(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    syntax = await diagram_engine.to_mermaid(db, session_id)
    return MermaidResponse(syntax=syntax)


@router.post("/{session_id}/diagram/export")
async def export_diagram(
    session_id: str,
    body: ExportRequest,
    db: AsyncSession = Depends(get_db),
):
    """Export the diagram in the specified format."""
    session = await session_manager.get(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if body.format == "json":
        state = await diagram_engine.get_full_state(db, session_id)
        return {
            "format": "json",
            "session_id": session_id,
            "title": session.title,
            "mode": session.mode_id,
            "diagram": state.model_dump(mode="json"),
        }
    elif body.format == "mermaid":
        syntax = await diagram_engine.to_mermaid(db, session_id)
        return {
            "format": "mermaid",
            "session_id": session_id,
            "syntax": syntax,
        }
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {body.format}. Use 'json' or 'mermaid'.",
        )
