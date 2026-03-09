"""Diagram state management and Mermaid generation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
from uuid import uuid4


@dataclass
class DiagramNode:
    id: str
    node_type: str  # start | question | answer | decision | info | research | summary | end
    label: str
    description: str = ""
    status: str = "pending"  # pending | active | answered | skipped
    metadata: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DiagramEdge:
    id: str
    source_id: str
    target_id: str
    label: str = ""
    edge_type: str = "flow"  # flow | decision | skip | research
    is_taken: bool = True
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


class DiagramGraph:
    """In-memory graph that generates Mermaid diagrams."""

    def __init__(self):
        self.nodes: dict[str, DiagramNode] = {}
        self.edges: dict[str, DiagramEdge] = {}
        self._current_node_id: Optional[str] = None

    @property
    def current_node_id(self) -> Optional[str]:
        return self._current_node_id

    @current_node_id.setter
    def current_node_id(self, value: Optional[str]):
        self._current_node_id = value

    def add_node(
        self,
        node_type: str,
        label: str,
        description: str = "",
        status: str = "pending",
        metadata: Optional[dict] = None,
        node_id: Optional[str] = None,
    ) -> DiagramNode:
        nid = node_id or str(uuid4())[:8]
        node = DiagramNode(
            id=nid,
            node_type=node_type,
            label=label,
            description=description,
            status=status,
            metadata=metadata or {},
        )
        self.nodes[nid] = node
        return node

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        label: str = "",
        edge_type: str = "flow",
        is_taken: bool = True,
    ) -> Optional[DiagramEdge]:
        if source_id not in self.nodes or target_id not in self.nodes:
            return None
        eid = str(uuid4())[:8]
        edge = DiagramEdge(
            id=eid,
            source_id=source_id,
            target_id=target_id,
            label=label,
            edge_type=edge_type,
            is_taken=is_taken,
        )
        self.edges[eid] = edge
        return edge

    def update_node_status(self, node_id: str, status: str):
        if node_id in self.nodes:
            self.nodes[node_id].status = status

    def add_question(
        self,
        question_text: str,
        category: str = "",
        choices: Optional[list[str]] = None,
        question_type: str = "free_text",
        reasoning: str = "",
    ) -> DiagramNode:
        """Add a question node and connect it to the current position."""
        node = self.add_node(
            node_type="question",
            label=self._truncate(question_text, 60),
            description=reasoning,
            status="active",
            metadata={
                "question_type": question_type,
                "choices": choices or [],
                "category": category,
                "full_text": question_text,
            },
        )

        # Connect to current node
        if self._current_node_id:
            self.add_edge(self._current_node_id, node.id, edge_type="flow")

        self._current_node_id = node.id
        return node

    def record_answer(self, answer: str, at_node_id: str = None) -> Optional[DiagramNode]:
        """Record user's answer to the current (or specified) question."""
        target_id = at_node_id or self._current_node_id
        if not target_id:
            return None

        current = self.nodes.get(target_id)
        if not current or current.node_type != "question":
            return None

        # Mark question as answered
        current.status = "answered"
        current.metadata["selected"] = answer

        # Create answer node
        answer_node = self.add_node(
            node_type="answer",
            label=self._truncate(answer, 60),
            status="answered",
            metadata={"full_text": answer},
        )

        # Connect with decision edge
        self.add_edge(
            target_id,
            answer_node.id,
            label=self._truncate(answer, 40),
            edge_type="decision",
            is_taken=True,
        )

        # Add untaken choice edges (ghost paths)
        choices = current.metadata.get("choices", [])
        for choice in choices:
            if choice != answer:
                ghost = self.add_node(
                    node_type="answer",
                    label=self._truncate(choice, 60),
                    status="skipped",
                    metadata={"full_text": choice},
                )
                self.add_edge(
                    target_id,
                    ghost.id,
                    label=self._truncate(choice, 40),
                    edge_type="decision",
                    is_taken=False,
                )

        self._current_node_id = answer_node.id
        return answer_node

    def add_info(self, label: str, description: str = "") -> DiagramNode:
        """Add an informational node."""
        node = self.add_node(
            node_type="info",
            label=self._truncate(label, 60),
            description=description,
            status="answered",
        )
        if self._current_node_id:
            self.add_edge(self._current_node_id, node.id, edge_type="flow")
        self._current_node_id = node.id
        return node

    def branch_answer(self, question_node_id: str, answer: str) -> Optional[DiagramNode]:
        """Create an alternative branch from an already-answered question."""
        question = self.nodes.get(question_node_id)
        if not question or question.node_type != "question":
            return None

        # Find existing ghost node for this answer
        for eid, edge in list(self.edges.items()):
            if edge.source_id == question_node_id and not edge.is_taken:
                target = self.nodes.get(edge.target_id)
                if target and (
                    target.label == self._truncate(answer, 60)
                    or target.metadata.get("full_text") == answer
                ):
                    target.status = "answered"
                    target.metadata["full_text"] = answer
                    edge.is_taken = True
                    self._current_node_id = target.id
                    return target

        # No matching ghost — create new answer node
        answer_node = self.add_node(
            node_type="answer",
            label=self._truncate(answer, 60),
            status="answered",
            metadata={"full_text": answer},
        )
        self.add_edge(
            question_node_id,
            answer_node.id,
            label=self._truncate(answer, 40),
            edge_type="decision",
            is_taken=True,
        )
        self._current_node_id = answer_node.id
        return answer_node

    def get_path_to_node(self, target_id: str) -> list[str]:
        """Get ordered node IDs from root to target by following taken edges."""
        if target_id not in self.nodes:
            return []
        parent_map: dict[str, str] = {}
        for edge in self.edges.values():
            if edge.is_taken:
                parent_map[edge.target_id] = edge.source_id
        path = []
        current: Optional[str] = target_id
        while current:
            path.append(current)
            current = parent_map.get(current)
        path.reverse()
        return path

    def get_qa_for_path(self, target_id: str) -> list[dict]:
        """Get Q&A history by walking the taken-edge path to target."""
        path = self.get_path_to_node(target_id)
        qa: list[dict] = []
        for i, nid in enumerate(path):
            node = self.nodes.get(nid)
            if node and node.node_type == "question" and node.status == "answered":
                answer_text = ""
                if i + 1 < len(path):
                    nxt = self.nodes.get(path[i + 1])
                    if nxt and nxt.node_type == "answer":
                        answer_text = nxt.metadata.get("full_text", nxt.label)
                if not answer_text:
                    answer_text = node.metadata.get("selected", "")
                qa.append({
                    "question": node.metadata.get("full_text", node.label),
                    "answer": answer_text,
                })
        return qa

    def add_summary(
        self, section_name: str, summary: str, key_decisions: list[str]
    ) -> DiagramNode:
        """Add a section summary node."""
        node = self.add_node(
            node_type="summary",
            label=f"Summary: {self._truncate(section_name, 40)}",
            description=summary,
            status="answered",
            metadata={"key_decisions": key_decisions},
        )
        if self._current_node_id:
            self.add_edge(
                self._current_node_id, node.id, label="Section Complete", edge_type="flow"
            )
        self._current_node_id = node.id
        return node

    def to_mermaid(self) -> str:
        """Generate Mermaid flowchart syntax."""
        lines = ["flowchart TD"]

        shape_map = {
            "start": ("([", "])"),
            "end": ("([", "])"),
            "question": ("{", "}"),
            "decision": ("{", "}"),
            "answer": ("[", "]"),
            "info": ("(", ")"),
            "research": ("[[", "]]"),
            "summary": ("([", "])"),
        }

        for node in self.nodes.values():
            nid = self._safe_id(node.id)
            label = self._escape_mermaid(node.label)
            open_b, close_b = shape_map.get(node.node_type, ("[", "]"))
            lines.append(f"    {nid}{open_b}\"{label}\"{close_b}")

        for edge in self.edges.values():
            src = self._safe_id(edge.source_id)
            tgt = self._safe_id(edge.target_id)
            label = self._escape_mermaid(edge.label)

            if edge.is_taken:
                arrow = "-->"
            else:
                arrow = "-.->"

            if label:
                lines.append(f"    {src} {arrow}|\"{label}\"| {tgt}")
            else:
                lines.append(f"    {src} {arrow} {tgt}")

        # Styles
        lines.append("")
        lines.append("    classDef question fill:#4F46E5,stroke:#3730A3,color:#fff")
        lines.append("    classDef answer fill:#059669,stroke:#047857,color:#fff")
        lines.append("    classDef info fill:#0891B2,stroke:#0E7490,color:#fff")
        lines.append("    classDef start fill:#7C3AED,stroke:#6D28D9,color:#fff")
        lines.append("    classDef summary fill:#D97706,stroke:#B45309,color:#fff")
        lines.append("    classDef skipped fill:#9CA3AF,stroke:#6B7280,color:#fff,stroke-dasharray: 5 5")
        lines.append("    classDef research fill:#EC4899,stroke:#DB2777,color:#fff")

        for node in self.nodes.values():
            nid = self._safe_id(node.id)
            if node.status == "skipped":
                lines.append(f"    class {nid} skipped")
            elif node.node_type in shape_map:
                lines.append(f"    class {nid} {node.node_type}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialize full graph state."""
        return {
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges.values()],
            "current_node_id": self._current_node_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DiagramGraph:
        """Deserialize graph state."""
        graph = cls()
        for nd in data.get("nodes", []):
            node = DiagramNode(**nd)
            graph.nodes[node.id] = node
        for ed in data.get("edges", []):
            edge = DiagramEdge(**ed)
            graph.edges[edge.id] = edge
        graph._current_node_id = data.get("current_node_id")
        return graph

    def get_stats(self) -> dict:
        """Get diagram statistics."""
        type_counts = {}
        for n in self.nodes.values():
            type_counts[n.node_type] = type_counts.get(n.node_type, 0) + 1
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "node_types": type_counts,
            "questions_asked": type_counts.get("question", 0),
            "questions_answered": sum(
                1 for n in self.nodes.values()
                if n.node_type == "question" and n.status == "answered"
            ),
        }

    def _safe_id(self, nid: str) -> str:
        return nid.replace("-", "_")

    def _escape_mermaid(self, text: str) -> str:
        text = text.replace('"', "'")
        text = text.replace("[", "(")
        text = text.replace("]", ")")
        text = text.replace("{", "(")
        text = text.replace("}", ")")
        text = text.replace("<", "‹")
        text = text.replace(">", "›")
        return text

    def _truncate(self, text: str, max_len: int) -> str:
        if len(text) <= max_len:
            return text
        return text[: max_len - 3] + "..."
