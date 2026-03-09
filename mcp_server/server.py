"""Solution Architect MCP Server.

Interactive consultation tool that uses a local LLM (Ollama) to generate
structured questions and builds real-time Mermaid workflow diagrams.
"""

from __future__ import annotations

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

from mcp_server.diagram import DiagramGraph
from mcp_server.modes import get_mode, list_modes
from mcp_server.ollama_client import generate_question, generate_summary
from mcp_server.sessions import SessionStore

# ── Server Setup ──────────────────────────────────────────────────────────

mcp = FastMCP(
    "Solution Architect",
    instructions="""You are a Solution Architect consultation assistant.

WORKFLOW:
1. User describes what they want to build → call `start_session` with a mode and their topic
2. Call `generate_next_question` — the local LLM generates a structured question with choices
3. Present the question and choices to the user
4. User picks a choice or types custom answer → call `answer_question`
5. Repeat steps 2-4. Show the diagram periodically with `get_diagram`
6. After 4-5 questions in a category, call `summarize_section`
7. Continue until all phases are covered

PRESENTING QUESTIONS:
When you get a question back from generate_next_question, present it like:
- Show the question text
- List the numbered choices
- Tell user they can pick a number or type their own answer

SHOWING DIAGRAMS:
When you call get_diagram, show the mermaid code in a ```mermaid block.
Do this after every 2-3 answers so the user sees the diagram grow.

IMPORTANT: The local LLM generates the questions. You just relay them and manage the flow.""",
)

store = SessionStore()
_diagrams: dict[str, DiagramGraph] = {}
_session_topics: dict[str, str] = {}  # session_id -> original topic
_session_qa: dict[str, list[dict]] = {}  # session_id -> [{question, answer}]


def _get_or_load_diagram(session_id: str) -> DiagramGraph:
    if session_id not in _diagrams:
        loaded = store.load_diagram(session_id)
        _diagrams[session_id] = loaded if loaded else DiagramGraph()
    return _diagrams[session_id]


def _save_diagram(session_id: str):
    if session_id in _diagrams:
        store.save_diagram(session_id, _diagrams[session_id])


def _get_qa_history(session_id: str) -> list[dict]:
    return _session_qa.get(session_id, [])


# ── Session Tools ─────────────────────────────────────────────────────────

@mcp.tool()
def list_consultation_modes() -> str:
    """List available consultation modes.

    Call this to show the user what types of consultations they can start.
    """
    modes = list_modes()
    lines = ["Available consultation modes:\n"]
    for m in modes:
        lines.append(f"**{m.name}** (`{m.id}`)")
        lines.append(f"  {m.description}")
        lines.append(f"  Phases: {', '.join(c.replace('_', ' ').title() for c in m.categories)}")
        lines.append("")
    return "\n".join(lines)


@mcp.tool()
def start_session(mode_id: str, topic: str, title: str = "") -> str:
    """Start a new consultation session with the user's topic.

    Args:
        mode_id: Consultation mode ('software_architecture', 'api_design',
                 'data_pipeline', 'cloud_migration', 'security_review')
        topic: The user's initial question or description of what they want to build
        title: Optional session title
    """
    try:
        mode = get_mode(mode_id)
    except ValueError as e:
        return str(e)

    session = store.create(mode_id, title or topic[:80])

    # Init diagram
    graph = DiagramGraph()
    graph.add_node("start", f"Start: {mode.name}", status="answered", node_id="start")
    graph.current_node_id = "start"

    # Add the user's topic as the first node
    topic_node = graph.add_info(label=graph._truncate(topic, 60), description=topic)
    graph.add_edge("start", topic_node.id, label="Topic", edge_type="flow")
    graph.current_node_id = topic_node.id

    _diagrams[session.id] = graph
    _session_topics[session.id] = topic
    _session_qa[session.id] = []
    _save_diagram(session.id)

    return (
        f"Session `{session.id}` created.\n"
        f"**Mode**: {mode.name}\n"
        f"**Topic**: {topic}\n"
        f"**Phases**: {', '.join(c.replace('_', ' ').title() for c in mode.categories)}\n\n"
        f"Now call `generate_next_question` with session_id=`{session.id}` to get the first question."
    )


@mcp.tool()
def list_sessions() -> str:
    """List all saved consultation sessions."""
    sessions = store.list_all()
    if not sessions:
        return "No saved sessions. Use `start_session` to begin."

    lines = ["Saved sessions:\n"]
    for s in sessions:
        lines.append(f"- `{s.id}` | **{s.title}** | {s.mode_id} | {s.status} | {s.updated_at[:16]}")
    return "\n".join(lines)


@mcp.tool()
def resume_session(session_id: str) -> str:
    """Resume a saved session. Loads diagram and Q&A history.

    Args:
        session_id: Session ID to resume
    """
    session = store.get(session_id)
    if not session:
        return f"Session `{session_id}` not found."

    mode = get_mode(session.mode_id)
    graph = _get_or_load_diagram(session_id)
    stats = graph.get_stats()
    store.update_status(session_id, "active")

    # Reconstruct Q&A history from diagram nodes
    if session_id not in _session_qa:
        qa = []
        for node in graph.nodes.values():
            if node.node_type == "question" and node.status == "answered":
                qa.append({
                    "question": node.metadata.get("full_text", node.label),
                    "answer": node.metadata.get("selected", ""),
                })
        _session_qa[session_id] = qa

    # Reconstruct topic
    if session_id not in _session_topics:
        _session_topics[session_id] = session.title

    result = (
        f"Session resumed: `{session.id}` — {session.title}\n"
        f"**Mode**: {mode.name} | **Progress**: {stats['questions_answered']} questions answered\n"
    )
    if session.conversation_summary:
        result += f"\n**Summary so far:**\n{session.conversation_summary}\n"

    result += f"\nCall `generate_next_question` with session_id=`{session.id}` to continue."
    return result


@mcp.tool()
def delete_session(session_id: str) -> str:
    """Delete a session.

    Args:
        session_id: Session ID to delete
    """
    if store.delete(session_id):
        _diagrams.pop(session_id, None)
        _session_topics.pop(session_id, None)
        _session_qa.pop(session_id, None)
        return f"Session `{session_id}` deleted."
    return f"Session `{session_id}` not found."


@mcp.tool()
def pause_session(session_id: str) -> str:
    """Pause a session for later.

    Args:
        session_id: Session ID to pause
    """
    session = store.get(session_id)
    if not session:
        return f"Session `{session_id}` not found."

    store.update_status(session_id, "paused")
    _save_diagram(session_id)
    _diagrams.pop(session_id, None)
    _session_topics.pop(session_id, None)
    _session_qa.pop(session_id, None)
    return f"Session `{session_id}` paused. Use `resume_session` to continue later."


# ── Question Generation & Answering ──────────────────────────────────────

@mcp.tool()
def generate_next_question(session_id: str) -> str:
    """Generate the next question using the local LLM (Ollama).

    Calls the local qwen3.5 model to generate a structured question with choices
    based on the topic and previous answers.

    Args:
        session_id: The active session ID

    Returns the question text and numbered choices. Present these to the user.
    """
    session = store.get(session_id)
    if not session:
        return f"Session `{session_id}` not found."

    mode = get_mode(session.mode_id)
    topic = _session_topics.get(session_id, session.title)
    qa_history = _get_qa_history(session_id)

    # Call Ollama to generate question
    result = generate_question(
        topic=topic,
        mode_context=f"{mode.name}: {mode.system_instructions[:200]}",
        qa_history=qa_history,
    )

    if not result:
        return (
            "Failed to generate question from LLM. "
            "Check that the OpenRouter API key is configured and the model is available."
        )

    # Add question node to diagram
    graph = _get_or_load_diagram(session_id)
    node = graph.add_question(
        question_text=result["question"],
        category=result["category"],
        choices=result["choices"],
        question_type="single_choice",
        reasoning=result["reasoning"],
    )
    _save_diagram(session_id)

    # Format for display
    lines = [
        f"**Question** (category: {result['category']}):\n",
        f"{result['question']}\n",
        "**Choices:**",
    ]
    for i, choice in enumerate(result["choices"], 1):
        lines.append(f"  {i}. {choice}")
    lines.append("")
    lines.append(f"_Why this matters: {result['reasoning']}_")
    lines.append("")
    lines.append(
        "Present this to the user. When they answer, call "
        f"`answer_question` with session_id=`{session_id}` and their answer."
    )

    return "\n".join(lines)


@mcp.tool()
def answer_question(session_id: str, answer: str) -> str:
    """Record the user's answer and update the diagram.

    Args:
        session_id: The active session ID
        answer: The user's answer (choice text or custom input)
    """
    graph = _get_or_load_diagram(session_id)
    if not graph.current_node_id:
        return "No active question. Call `generate_next_question` first."

    current = graph.nodes.get(graph.current_node_id)
    if not current or current.node_type != "question":
        return "No active question. Call `generate_next_question` first."

    # Record in diagram
    graph.record_answer(answer)
    _save_diagram(session_id)

    # Track in Q&A history
    qa_list = _session_qa.setdefault(session_id, [])
    qa_list.append({
        "question": current.metadata.get("full_text", current.label),
        "answer": answer,
    })

    stats = graph.get_stats()
    return (
        f"Answer recorded: \"{answer}\"\n"
        f"Progress: {stats['questions_answered']} questions answered, {stats['total_nodes']} diagram nodes.\n\n"
        f"Call `generate_next_question` for the next question, "
        f"or `get_diagram` to show the current diagram."
    )


# ── Diagram & Export ──────────────────────────────────────────────────────

@mcp.tool()
def get_diagram(session_id: str) -> str:
    """Get the current diagram as Mermaid syntax.

    Show this in a ```mermaid code block for the user to see.

    Args:
        session_id: The active session ID
    """
    graph = _get_or_load_diagram(session_id)
    stats = graph.get_stats()

    if stats["total_nodes"] == 0:
        return "Diagram is empty. Start with `start_session`."

    mermaid = graph.to_mermaid()
    return (
        f"Diagram: {stats['total_nodes']} nodes, "
        f"{stats['questions_answered']}/{stats['questions_asked']} answered\n\n"
        f"```mermaid\n{mermaid}\n```"
    )


@mcp.tool()
def summarize_section(session_id: str) -> str:
    """Ask the local LLM to summarize the current Q&A section.

    Call this after 4-5 questions to create a summary node in the diagram.

    Args:
        session_id: The active session ID
    """
    session = store.get(session_id)
    if not session:
        return f"Session `{session_id}` not found."

    topic = _session_topics.get(session_id, session.title)
    qa_history = _get_qa_history(session_id)

    if not qa_history:
        return "No Q&A to summarize yet."

    result = generate_summary(topic, qa_history)

    graph = _get_or_load_diagram(session_id)

    if result:
        graph.add_summary(
            section_name=result.get("next_area", "Section"),
            summary=result.get("summary", ""),
            key_decisions=result.get("key_decisions", []),
        )

        # Update session summary
        existing = session.conversation_summary or ""
        new_summary = (
            existing + f"\n\n{result.get('summary', '')}\n"
            f"Decisions: {'; '.join(result.get('key_decisions', []))}"
        )
        store.update_summary(session_id, new_summary.strip())
    else:
        # Fallback if LLM fails
        decisions = [f"{qa['question']} → {qa['answer']}" for qa in qa_history[-5:]]
        graph.add_summary(
            section_name="Progress",
            summary=f"Covered {len(qa_history)} questions so far.",
            key_decisions=decisions,
        )

    _save_diagram(session_id)
    stats = graph.get_stats()

    return (
        f"Section summarized and added to diagram.\n"
        f"Diagram: {stats['total_nodes']} nodes.\n\n"
        f"Call `generate_next_question` to continue, or `get_diagram` to view."
    )


@mcp.tool()
def export_session(session_id: str, format: str = "json") -> str:
    """Export a session as JSON, Mermaid, or text summary.

    Args:
        session_id: Session ID to export
        format: 'json', 'mermaid', or 'summary'
    """
    session = store.get(session_id)
    if not session:
        return f"Session `{session_id}` not found."

    graph = _get_or_load_diagram(session_id)

    if format == "mermaid":
        return graph.to_mermaid()

    elif format == "summary":
        stats = graph.get_stats()
        mode = get_mode(session.mode_id)
        lines = [
            f"# {session.title}",
            f"**Mode**: {mode.name}",
            f"**Stats**: {stats['questions_answered']} questions answered",
            "",
        ]
        if session.conversation_summary:
            lines.append(session.conversation_summary)
        lines.append("")
        lines.append(f"```mermaid\n{graph.to_mermaid()}\n```")
        return "\n".join(lines)

    else:
        return json.dumps({
            "session": {
                "id": session.id,
                "title": session.title,
                "mode_id": session.mode_id,
                "status": session.status,
                "summary": session.conversation_summary,
            },
            "qa_history": _get_qa_history(session_id),
            "diagram": graph.to_dict(),
            "stats": graph.get_stats(),
        }, indent=2)


# ── Run ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
