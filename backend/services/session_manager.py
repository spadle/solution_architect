import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.session import Session
from backend.models.message import Message
from backend.models.diagram import DiagramNode, DiagramEdge

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages session CRUD and state."""

    async def create(
        self, db: AsyncSession, mode_id: str, title: Optional[str] = None
    ) -> Session:
        session = Session(
            mode_id=mode_id,
            title=title or "Untitled Session",
            status="active",
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    async def get(self, db: AsyncSession, session_id: str) -> Optional[Session]:
        result = await db.execute(
            select(Session)
            .where(Session.id == session_id)
            .options(
                selectinload(Session.messages),
                selectinload(Session.diagram_nodes),
                selectinload(Session.diagram_edges),
            )
        )
        return result.scalar_one_or_none()

    async def list_all(self, db: AsyncSession) -> list[Session]:
        result = await db.execute(
            select(Session).order_by(Session.updated_at.desc())
        )
        return list(result.scalars().all())

    async def update(
        self,
        db: AsyncSession,
        session_id: str,
        title: Optional[str] = None,
        status: Optional[str] = None,
        current_node_id: Optional[str] = None,
        context_summary: Optional[str] = None,
    ) -> Optional[Session]:
        session = await self.get(db, session_id)
        if not session:
            return None
        if title is not None:
            session.title = title
        if status is not None:
            session.status = status
        if current_node_id is not None:
            session.current_node_id = current_node_id
        if context_summary is not None:
            session.context_summary = context_summary
        await db.commit()
        await db.refresh(session)
        return session

    async def delete(self, db: AsyncSession, session_id: str) -> bool:
        session = await self.get(db, session_id)
        if not session:
            return False
        await db.delete(session)
        await db.commit()
        return True

    async def add_message(
        self,
        db: AsyncSession,
        session_id: str,
        role: str,
        content: str,
        structured_data: Optional[dict] = None,
        node_id: Optional[str] = None,
    ) -> Message:
        # Get next sequence number
        result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.sequence.desc())
            .limit(1)
        )
        last_msg = result.scalar_one_or_none()
        sequence = (last_msg.sequence + 1) if last_msg else 1

        message = Message(
            session_id=session_id,
            sequence=sequence,
            role=role,
            content=content,
            structured_data=structured_data,
            node_id=node_id,
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message

    async def get_messages(
        self, db: AsyncSession, session_id: str
    ) -> list[Message]:
        result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.sequence)
        )
        return list(result.scalars().all())

    async def get_message_count(
        self, db: AsyncSession, session_id: str
    ) -> int:
        messages = await self.get_messages(db, session_id)
        return len(messages)


session_manager = SessionManager()
