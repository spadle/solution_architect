"""Session persistence using SQLite."""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from mcp_server.diagram import DiagramGraph

_default_db = Path("/tmp/sessions.db") if os.environ.get("VERCEL") else Path(__file__).parent / "sessions.db"
DB_PATH = _default_db


@dataclass
class SessionRecord:
    id: str
    title: str
    mode_id: str
    status: str  # active | paused | completed
    diagram_data: str  # JSON serialized DiagramGraph
    conversation_summary: str
    created_at: str
    updated_at: str


class SessionStore:
    """SQLite-backed session persistence."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self._init_db()

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    mode_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    diagram_data TEXT NOT NULL DEFAULT '{}',
                    conversation_summary TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def create(self, mode_id: str, title: str = "") -> SessionRecord:
        now = datetime.utcnow().isoformat()
        session = SessionRecord(
            id=str(uuid4())[:8],
            title=title or f"Session {now[:10]}",
            mode_id=mode_id,
            status="active",
            diagram_data="{}",
            conversation_summary="",
            created_at=now,
            updated_at=now,
        )
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO sessions (id, title, mode_id, status, diagram_data,
                   conversation_summary, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session.id, session.title, session.mode_id, session.status,
                    session.diagram_data, session.conversation_summary,
                    session.created_at, session.updated_at,
                ),
            )
        return session

    def get(self, session_id: str) -> Optional[SessionRecord]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
        if not row:
            return None
        return SessionRecord(*row)

    def list_all(self) -> list[SessionRecord]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM sessions ORDER BY updated_at DESC"
            ).fetchall()
        return [SessionRecord(*r) for r in rows]

    def save_diagram(self, session_id: str, graph: DiagramGraph):
        now = datetime.utcnow().isoformat()
        data = json.dumps(graph.to_dict())
        with self._conn() as conn:
            conn.execute(
                "UPDATE sessions SET diagram_data = ?, updated_at = ? WHERE id = ?",
                (data, now, session_id),
            )

    def load_diagram(self, session_id: str) -> Optional[DiagramGraph]:
        session = self.get(session_id)
        if not session or not session.diagram_data:
            return None
        try:
            data = json.loads(session.diagram_data)
            if not data:
                return None
            return DiagramGraph.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None

    def update_summary(self, session_id: str, summary: str):
        now = datetime.utcnow().isoformat()
        with self._conn() as conn:
            conn.execute(
                "UPDATE sessions SET conversation_summary = ?, updated_at = ? WHERE id = ?",
                (summary, now, session_id),
            )

    def update_status(self, session_id: str, status: str):
        now = datetime.utcnow().isoformat()
        with self._conn() as conn:
            conn.execute(
                "UPDATE sessions SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, session_id),
            )

    def update_title(self, session_id: str, title: str):
        now = datetime.utcnow().isoformat()
        with self._conn() as conn:
            conn.execute(
                "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
                (title, now, session_id),
            )

    def delete(self, session_id: str) -> bool:
        with self._conn() as conn:
            cursor = conn.execute(
                "DELETE FROM sessions WHERE id = ?", (session_id,)
            )
        return cursor.rowcount > 0
