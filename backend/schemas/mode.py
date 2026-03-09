from pydantic import BaseModel


class ModeResponse(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    question_categories: list[str]
    initial_question: str
