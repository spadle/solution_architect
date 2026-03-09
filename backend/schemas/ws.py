from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from backend.schemas.diagram import DiagramNodeSchema, DiagramEdgeSchema


class DiagramEvent(BaseModel):
    type: Literal[
        "node_added",
        "node_updated",
        "edge_added",
        "edge_updated",
        "section_complete",
        "full_sync",
        "error",
    ]
    node: Optional[DiagramNodeSchema] = None
    edge: Optional[DiagramEdgeSchema] = None
    metadata: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
