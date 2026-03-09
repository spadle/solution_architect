from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MessageCreate(BaseModel):
    content: str
    choice_index: Optional[int] = None


class QuestionData(BaseModel):
    question_text: str
    question_type: str  # single_choice | multiple_choice | free_text | yes_no | scale
    choices: list[str] = []
    category: str
    reasoning: str


class MessageResponse(BaseModel):
    id: str
    session_id: str
    sequence: int
    role: str
    content: str
    structured_data: Optional[dict] = None
    node_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    message: MessageResponse
    question: Optional[QuestionData] = None
    diagram_updates: int = 0
