import logging
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.engine.graph_ops import (
    calculate_node_position,
    generate_node_id,
    nodes_edges_to_mermaid,
)
from backend.models.diagram import DiagramEdge, DiagramNode
from backend.schemas.diagram import DiagramEdgeSchema, DiagramNodeSchema, DiagramState
from backend.schemas.ws import DiagramEvent

logger = logging.getLogger(__name__)


class DiagramEngine:
    """Manages the diagram graph: adds nodes, edges, handles layout."""

    async def create_start_node(
        self, db: AsyncSession, session_id: str, mode_name: str
    ) -> DiagramNode:
        """Create the initial start node for a new session."""
        node = DiagramNode(
            id=generate_node_id(),
            session_id=session_id,
            node_type="start",
            label=f"Start: {mode_name}",
            status="answered",
            position_x=0.0,
            position_y=0.0,
        )
        db.add(node)
        await db.commit()
        await db.refresh(node)
        return node

    async def add_question_node(
        self,
        db: AsyncSession,
        session_id: str,
        question_data: dict[str, Any],
        parent_node_id: Optional[str] = None,
    ) -> tuple[DiagramNode, Optional[DiagramEdge]]:
        """Create a question node and connect it to the parent node."""
        depth = await self._get_depth(db, session_id)

        node = DiagramNode(
            id=generate_node_id(),
            session_id=session_id,
            node_type="question",
            label=self._truncate(question_data["question_text"], 80),
            description=question_data.get("reasoning"),
            status="active",
            metadata_={
                "question_type": question_data["question_type"],
                "choices": question_data.get("choices", []),
                "category": question_data["category"],
            },
        )
        node.position_x, node.position_y = calculate_node_position(depth, 0, 1)
        db.add(node)

        edge = None
        if parent_node_id:
            edge = DiagramEdge(
                id=generate_node_id(),
                session_id=session_id,
                source_node_id=parent_node_id,
                target_node_id=node.id,
                edge_type="flow",
                is_taken=True,
            )
            db.add(edge)

        await db.commit()
        await db.refresh(node)
        if edge:
            await db.refresh(edge)
        return node, edge

    async def record_answer(
        self,
        db: AsyncSession,
        session_id: str,
        question_node_id: str,
        answer: str,
    ) -> tuple[DiagramNode, DiagramEdge]:
        """Record the user's answer: create answer node, update question status."""
        question_node = await db.get(DiagramNode, question_node_id)
        if question_node:
            question_node.status = "answered"
            if question_node.metadata_:
                question_node.metadata_ = {
                    **question_node.metadata_,
                    "selected": answer,
                }

        depth = await self._get_depth(db, session_id)
        answer_node = DiagramNode(
            id=generate_node_id(),
            session_id=session_id,
            node_type="answer",
            label=self._truncate(answer, 80),
            status="answered",
        )
        answer_node.position_x, answer_node.position_y = calculate_node_position(
            depth, 0, 1
        )
        db.add(answer_node)

        edge = DiagramEdge(
            id=generate_node_id(),
            session_id=session_id,
            source_node_id=question_node_id,
            target_node_id=answer_node.id,
            label=self._truncate(answer, 50),
            edge_type="decision",
            is_taken=True,
        )
        db.add(edge)

        await db.commit()
        await db.refresh(answer_node)
        await db.refresh(edge)
        return answer_node, edge

    async def apply_updates(
        self,
        db: AsyncSession,
        session_id: str,
        update_data: dict[str, Any],
        existing_node_ids: Optional[set[str]] = None,
    ) -> list[dict[str, Any]]:
        """Apply batch node/edge updates from Claude's update_diagram tool call."""
        events = []
        temp_to_real: dict[str, str] = {}

        # Gather existing node IDs if not provided
        if existing_node_ids is None:
            existing_node_ids = await self._get_all_node_ids(db, session_id)

        depth = await self._get_depth(db, session_id)

        # Create nodes
        nodes_data = update_data.get("nodes", [])
        for i, node_data in enumerate(nodes_data):
            real_id = generate_node_id()
            temp_to_real[node_data["temp_id"]] = real_id

            node = DiagramNode(
                id=real_id,
                session_id=session_id,
                node_type=node_data["node_type"],
                label=self._truncate(node_data["label"], 80),
                description=node_data.get("description"),
                status="pending",
            )
            node.position_x, node.position_y = calculate_node_position(
                depth + 1, i, len(nodes_data)
            )
            db.add(node)
            events.append(
                DiagramEvent(
                    type="node_added",
                    node=DiagramNodeSchema(
                        id=real_id,
                        session_id=session_id,
                        node_type=node.node_type,
                        label=node.label,
                        description=node.description,
                        status=node.status,
                        metadata=node.metadata_,
                        position_x=node.position_x,
                        position_y=node.position_y,
                        created_at=node.created_at,
                    ),
                ).model_dump(mode="json")
            )

        # Create edges
        for edge_data in update_data.get("edges", []):
            src_id = self._resolve_id(
                edge_data["source_id"], temp_to_real, existing_node_ids
            )
            tgt_id = self._resolve_id(
                edge_data["target_id"], temp_to_real, existing_node_ids
            )
            if not src_id or not tgt_id:
                logger.warning(
                    f"Could not resolve edge: {edge_data['source_id']} -> {edge_data['target_id']}"
                )
                continue

            edge = DiagramEdge(
                id=generate_node_id(),
                session_id=session_id,
                source_node_id=src_id,
                target_node_id=tgt_id,
                label=edge_data.get("label"),
                edge_type=edge_data.get("edge_type", "flow"),
                is_taken=True,
            )
            db.add(edge)
            events.append(
                DiagramEvent(
                    type="edge_added",
                    edge=DiagramEdgeSchema(
                        id=edge.id,
                        session_id=session_id,
                        source_node_id=src_id,
                        target_node_id=tgt_id,
                        label=edge.label,
                        edge_type=edge.edge_type,
                        is_taken=edge.is_taken,
                        created_at=edge.created_at,
                    ),
                ).model_dump(mode="json")
            )

        await db.commit()
        return events

    async def add_summary_node(
        self,
        db: AsyncSession,
        session_id: str,
        section_data: dict[str, Any],
        parent_node_id: Optional[str] = None,
    ) -> DiagramNode:
        """Add a summary node for a completed section."""
        depth = await self._get_depth(db, session_id)
        node = DiagramNode(
            id=generate_node_id(),
            session_id=session_id,
            node_type="summary",
            label=f"Summary: {section_data['section_name']}",
            description=section_data["summary"],
            status="answered",
            metadata_={
                "key_decisions": section_data["key_decisions"],
                "next_section": section_data.get("next_section"),
            },
        )
        node.position_x, node.position_y = calculate_node_position(depth, 0, 1)
        db.add(node)

        if parent_node_id:
            edge = DiagramEdge(
                id=generate_node_id(),
                session_id=session_id,
                source_node_id=parent_node_id,
                target_node_id=node.id,
                label="Section Complete",
                edge_type="flow",
                is_taken=True,
            )
            db.add(edge)

        await db.commit()
        await db.refresh(node)
        return node

    async def get_full_state(
        self, db: AsyncSession, session_id: str
    ) -> DiagramState:
        """Get the complete diagram state."""
        nodes_result = await db.execute(
            select(DiagramNode)
            .where(DiagramNode.session_id == session_id)
            .order_by(DiagramNode.created_at)
        )
        edges_result = await db.execute(
            select(DiagramEdge)
            .where(DiagramEdge.session_id == session_id)
            .order_by(DiagramEdge.created_at)
        )

        nodes = [
            DiagramNodeSchema(
                id=n.id,
                session_id=n.session_id,
                node_type=n.node_type,
                label=n.label,
                description=n.description,
                status=n.status,
                metadata=n.metadata_,
                position_x=n.position_x,
                position_y=n.position_y,
                created_at=n.created_at,
            )
            for n in nodes_result.scalars().all()
        ]
        edges = [
            DiagramEdgeSchema(
                id=e.id,
                session_id=e.session_id,
                source_node_id=e.source_node_id,
                target_node_id=e.target_node_id,
                label=e.label,
                edge_type=e.edge_type,
                is_taken=e.is_taken,
                created_at=e.created_at,
            )
            for e in edges_result.scalars().all()
        ]

        return DiagramState(nodes=nodes, edges=edges)

    async def to_mermaid(self, db: AsyncSession, session_id: str) -> str:
        """Convert diagram to Mermaid syntax."""
        state = await self.get_full_state(db, session_id)
        nodes = [n.model_dump() for n in state.nodes]
        edges = [e.model_dump() for e in state.edges]
        return nodes_edges_to_mermaid(nodes, edges)

    async def _get_depth(self, db: AsyncSession, session_id: str) -> int:
        result = await db.execute(
            select(DiagramNode).where(DiagramNode.session_id == session_id)
        )
        return len(list(result.scalars().all()))

    async def _get_all_node_ids(
        self, db: AsyncSession, session_id: str
    ) -> set[str]:
        result = await db.execute(
            select(DiagramNode.id).where(DiagramNode.session_id == session_id)
        )
        return {row[0] for row in result.all()}

    def _resolve_id(
        self,
        ref_id: str,
        temp_to_real: dict[str, str],
        existing_ids: set[str],
    ) -> Optional[str]:
        if ref_id in temp_to_real:
            return temp_to_real[ref_id]
        if ref_id in existing_ids:
            return ref_id
        return None

    def _truncate(self, text: str, max_len: int) -> str:
        if len(text) <= max_len:
            return text
        return text[: max_len - 3] + "..."


diagram_engine = DiagramEngine()
