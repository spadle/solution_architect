from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    title: Mapped[str] = mapped_column(String(255), default="Untitled Session")
    mode_id: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="active"
    )  # active | paused | completed
    current_node_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True
    )
    context_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="session",
        order_by="Message.sequence",
        cascade="all, delete-orphan",
    )
    diagram_nodes: Mapped[list["DiagramNode"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    diagram_edges: Mapped[list["DiagramEdge"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
