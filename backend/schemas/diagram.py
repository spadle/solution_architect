from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DiagramNodeSchema(BaseModel):
    id: str
    session_id: str
    node_type: str
    label: str
    description: Optional[str] = None
    status: str
    metadata: Optional[dict] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DiagramEdgeSchema(BaseModel):
    id: str
    session_id: str
    source_node_id: str
    target_node_id: str
    label: Optional[str] = None
    edge_type: str
    is_taken: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class DiagramState(BaseModel):
    nodes: list[DiagramNodeSchema]
    edges: list[DiagramEdgeSchema]


class ExportRequest(BaseModel):
    format: str  # json | mermaid | png


class MermaidResponse(BaseModel):
    syntax: str
