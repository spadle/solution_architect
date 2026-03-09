from fastapi import APIRouter

from backend.schemas.mode import ModeResponse
from backend.services.mode_registry import list_modes, get_mode

router = APIRouter()


@router.get("", response_model=list[ModeResponse])
async def get_modes():
    """List all available consultation modes."""
    modes = list_modes()
    return [
        ModeResponse(
            id=m.id,
            name=m.name,
            description=m.description,
            icon=m.icon,
            question_categories=m.question_categories,
            initial_question=m.initial_question,
        )
        for m in modes
    ]


@router.get("/{mode_id}", response_model=ModeResponse)
async def get_mode_detail(mode_id: str):
    """Get details for a specific mode."""
    m = get_mode(mode_id)
    return ModeResponse(
        id=m.id,
        name=m.name,
        description=m.description,
        icon=m.icon,
        question_categories=m.question_categories,
        initial_question=m.initial_question,
    )
