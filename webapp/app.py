"""Solution Architect Web App.

Lightweight FastAPI server with interactive diagram UI.
Reuses mcp_server modules for diagram, sessions, and Ollama integration.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from mcp_server.diagram import DiagramGraph
from mcp_server.modes import get_mode, list_modes
from mcp_server.ollama_client import (
    generate_branch_name,
    generate_doc,
    generate_question,
    generate_summary,
    generate_title,
)
from mcp_server.sessions import SessionStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Solution Architect")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

store = SessionStore()
_diagrams: dict[str, DiagramGraph] = {}
_topics: dict[str, str] = {}
_qa: dict[str, list[dict]] = {}
_languages: dict[str, str] = {}


def _get_graph(sid: str) -> DiagramGraph:
    if sid not in _diagrams:
        loaded = store.load_diagram(sid)
        _diagrams[sid] = loaded if loaded else DiagramGraph()
    return _diagrams[sid]


def _save(sid: str):
    if sid in _diagrams:
        store.save_diagram(sid, _diagrams[sid])


# ── Models ────────────────────────────────────────────────────────────────

class StartRequest(BaseModel):
    mode_id: str
    topic: str
    language: str = "en"


class AnswerRequest(BaseModel):
    session_id: str
    answer: str
    question_node_id: str = ""


class BranchRequest(BaseModel):
    session_id: str
    question_node_id: str
    answer: str


class SessionIdRequest(BaseModel):
    session_id: str


class GenerateDocRequest(BaseModel):
    session_id: str
    doc_type: str = "architecture"


# ── Pages ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


# ── API ───────────────────────────────────────────────────────────────────

@app.get("/api/modes")
async def api_modes(language: str = "en"):
    return list_modes(language=language)


@app.get("/api/sessions")
async def api_sessions():
    return [
        {
            "id": s.id, "title": s.title, "mode_id": s.mode_id,
            "status": s.status, "updated_at": s.updated_at,
        }
        for s in store.list_all()
    ]


@app.post("/api/start")
async def api_start(req: StartRequest):
    """Start session and immediately generate the first question."""
    try:
        mode = get_mode(req.mode_id)
    except ValueError as e:
        raise HTTPException(400, str(e))

    session = store.create(req.mode_id, req.topic[:80])
    sid = session.id

    graph = DiagramGraph()
    graph.add_node("start", f"Start: {mode.name}", status="answered", node_id="start")
    graph.current_node_id = "start"

    topic_node = graph.add_info(
        label=graph._truncate(req.topic, 60), description=req.topic
    )

    _diagrams[sid] = graph
    _topics[sid] = req.topic
    _qa[sid] = []
    _languages[sid] = req.language
    _save(sid)

    lang = req.language

    # Generate title and first question concurrently
    title_result, question = await asyncio.gather(
        asyncio.to_thread(generate_title, req.topic, lang),
        asyncio.to_thread(
            generate_question,
            req.topic,
            f"{mode.name}: {mode.system_instructions[:300]}",
            [],
            lang,
        ),
    )

    generated_title = title_result or req.topic[:40]

    if question:
        graph.add_question(
            question_text=question["question"],
            category=question["category"],
            choices=question["choices"],
            question_type="single_choice",
            reasoning=question["reasoning"],
        )
        _save(sid)

    return {
        "session_id": sid,
        "title": generated_title,
        "question": question,
        "diagram": _build_diagram_response(sid),
    }


@app.post("/api/answer")
async def api_answer(req: AnswerRequest):
    """Record answer and generate next question."""
    sid = req.session_id
    session = store.get(sid)
    if not session:
        raise HTTPException(404, "Session not found")

    graph = _get_graph(sid)
    mode = get_mode(session.mode_id)

    # Record the answer at the specified (or current) question
    q_id = req.question_node_id or graph.current_node_id
    target = graph.nodes.get(q_id) if q_id else None
    if target and target.node_type == "question" and target.status == "active":
        graph.record_answer(req.answer, at_node_id=q_id)
        _qa.setdefault(sid, []).append({
            "question": target.metadata.get("full_text", target.label),
            "answer": req.answer,
        })
        _save(sid)

    # Use path-based QA for contextual question generation
    topic = _topics.get(sid, session.title)
    qa_history = graph.get_qa_for_path(graph.current_node_id)
    lang = _languages.get(sid, "en")

    question = generate_question(
        topic=topic,
        mode_context=f"{mode.name}: {mode.system_instructions[:300]}",
        qa_history=qa_history,
        language=lang,
    )

    if question:
        graph.add_question(
            question_text=question["question"],
            category=question["category"],
            choices=question["choices"],
            question_type="single_choice",
            reasoning=question["reasoning"],
        )
        _save(sid)

    return {
        "session_id": sid,
        "question": question,
        "diagram": _build_diagram_response(sid),
        "stats": graph.get_stats(),
        "completed": question is None,
    }


@app.post("/api/branch")
async def api_branch(req: BranchRequest):
    """Branch from an already-answered question with a different choice."""
    sid = req.session_id
    session = store.get(sid)
    if not session:
        raise HTTPException(404, "Session not found")

    graph = _get_graph(sid)
    mode = get_mode(session.mode_id)

    branch_node = graph.branch_answer(req.question_node_id, req.answer)
    if not branch_node:
        raise HTTPException(400, "Cannot branch from this node")

    _qa.setdefault(sid, []).append({
        "question": graph.nodes[req.question_node_id].metadata.get("full_text", ""),
        "answer": req.answer,
    })
    _save(sid)

    # Generate branch name and next question concurrently
    topic = _topics.get(sid, session.title)
    qa_history = graph.get_qa_for_path(graph.current_node_id)
    lang = _languages.get(sid, "en")

    branch_name_result, question = await asyncio.gather(
        asyncio.to_thread(generate_branch_name, topic, req.answer, lang),
        asyncio.to_thread(
            generate_question,
            topic,
            f"{mode.name}: {mode.system_instructions[:300]}",
            qa_history,
            lang,
        ),
    )

    if question:
        graph.add_question(
            question_text=question["question"],
            category=question["category"],
            choices=question["choices"],
            question_type="single_choice",
            reasoning=question["reasoning"],
        )
        _save(sid)

    return {
        "session_id": sid,
        "question": question,
        "branch_name": branch_name_result or req.answer[:25],
        "diagram": _build_diagram_response(sid),
        "stats": graph.get_stats(),
        "completed": question is None,
    }


@app.post("/api/summarize")
async def api_summarize(req: SessionIdRequest):
    """Summarize current section."""
    sid = req.session_id
    session = store.get(sid)
    if not session:
        raise HTTPException(404, "Session not found")

    topic = _topics.get(sid, session.title)
    qa_history = _qa.get(sid, [])
    graph = _get_graph(sid)
    lang = _languages.get(sid, "en")

    result = generate_summary(topic, qa_history, language=lang)
    if result:
        graph.add_summary(
            result.get("next_area", "Section"),
            result.get("summary", ""),
            result.get("key_decisions", []),
        )
    _save(sid)

    return {
        "session_id": sid,
        "summary": result,
        "diagram": _build_diagram_response(sid),
    }


@app.post("/api/generate-doc")
async def api_generate_doc(req: GenerateDocRequest):
    """Generate architecture or documentation from consultation."""
    sid = req.session_id
    session = store.get(sid)
    if not session:
        raise HTTPException(404, "Session not found")

    topic = _topics.get(sid, session.title)
    qa_history = _qa.get(sid, [])
    lang = _languages.get(sid, "en")

    content = await asyncio.to_thread(
        generate_doc, topic, qa_history, req.doc_type, lang
    )

    return {"session_id": sid, "content": content, "doc_type": req.doc_type}


@app.get("/api/diagram/{session_id}")
async def api_diagram(session_id: str):
    graph = _get_graph(session_id)
    return _build_diagram_response(session_id)


@app.get("/api/export/{session_id}")
async def api_export(session_id: str, format: str = "json"):
    session = store.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    graph = _get_graph(session_id)

    if format == "mermaid":
        return {"mermaid": graph.to_mermaid()}
    else:
        return {
            "session": {"id": session.id, "title": session.title, "mode_id": session.mode_id},
            "qa_history": _qa.get(session_id, []),
            "diagram": graph.to_dict(),
            "stats": graph.get_stats(),
        }


@app.delete("/api/sessions/{session_id}")
async def api_delete(session_id: str):
    store.delete(session_id)
    _diagrams.pop(session_id, None)
    _topics.pop(session_id, None)
    _qa.pop(session_id, None)
    _languages.pop(session_id, None)
    return {"ok": True}


def _build_diagram_response(sid: str) -> dict:
    """Build diagram data for the frontend (nodes + edges + mermaid)."""
    graph = _get_graph(sid)
    # Deduplicate edges (safety net against stale bytecode)
    seen_edges: set[tuple[str, str]] = set()
    unique_edges: list[dict] = []
    for e in graph.edges.values():
        key = (e.source_id, e.target_id)
        if key not in seen_edges:
            seen_edges.add(key)
            unique_edges.append(e.to_dict())
    return {
        "nodes": [n.to_dict() for n in graph.nodes.values()],
        "edges": unique_edges,
        "current_node_id": graph.current_node_id,
        "mermaid": graph.to_mermaid(),
        "stats": graph.get_stats(),
    }
