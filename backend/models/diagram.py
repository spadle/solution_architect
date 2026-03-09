from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class DiagramNode(Base):
    __tablename__ = "diagram_nodes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions.id"), nullable=False
    )
    node_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # question | decision | answer | info | start | end | research | summary
    label: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending | active | answered | skipped
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSON, nullable=True
    )
    position_x: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    position_y: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    session: Mapped["Session"] = relationship(back_populates="diagram_nodes")


class DiagramEdge(Base):
    __tablename__ = "diagram_edges"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions.id"), nullable=False
    )
    source_node_id: Mapped[str] = mapped_column(
        ForeignKey("diagram_nodes.id"), nullable=False
    )
    target_node_id: Mapped[str] = mapped_column(
        ForeignKey("diagram_nodes.id"), nullable=False
    )
    label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    edge_type: Mapped[str] = mapped_column(
        String(20), default="flow"
    )  # flow | decision | skip | research
    is_taken: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    session: Mapped["Session"] = relationship(back_populates="diagram_edges")
    source_node: Mapped["DiagramNode"] = relationship(foreign_keys=[source_node_id])
    target_node: Mapped["DiagramNode"] = relationship(foreign_keys=[target_node_id])
