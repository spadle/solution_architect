import logging
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.engine.prompts import RESUME_PROMPT_TEMPLATE
from backend.engine.tools import CONVERSATION_TOOLS
from backend.schemas.diagram import DiagramNodeSchema, DiagramEdgeSchema
from backend.schemas.message import ConversationResponse, MessageResponse, QuestionData
from backend.schemas.ws import DiagramEvent
from backend.services.claude_client import claude_client
from backend.services.diagram_engine import diagram_engine
from backend.services.mode_registry import get_mode
from backend.services.session_manager import session_manager
from backend.services.ws_manager import ws_manager

logger = logging.getLogger(__name__)


class ConversationEngine:
    """Core orchestrator: manages conversation flow, tool calls, and diagram updates."""

    async def start_session(
        self, db: AsyncSession, session_id: str
    ) -> ConversationResponse:
        """Initialize a new session with the start node and first AI message."""
        session = await session_manager.get(db, session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        mode = get_mode(session.mode_id)

        # Create start node
        start_node = await diagram_engine.create_start_node(
            db, session_id, mode.name
        )
        await self._broadcast_node(session_id, start_node, db)

        # Update session with current node
        await session_manager.update(
            db, session_id, current_node_id=start_node.id
        )

        # Generate initial AI message using Claude
        messages = [
            {
                "role": "user",
                "content": "Please start the consultation. Introduce yourself briefly and ask your first question using the ask_question tool.",
            }
        ]

        response = await claude_client.create_message(
            system=mode.system_prompt,
            messages=messages,
            tools=CONVERSATION_TOOLS,
        )

        return await self._process_response(
            db, session_id, response, is_initial=True
        )

    async def process_message(
        self, db: AsyncSession, session_id: str, user_input: str
    ) -> ConversationResponse:
        """Process a user message and generate AI response with diagram updates."""
        session = await session_manager.get(db, session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        mode = get_mode(session.mode_id)

        # Record user's answer in diagram if there's an active question node
        if session.current_node_id:
            answer_node, answer_edge = await diagram_engine.record_answer(
                db, session_id, session.current_node_id, user_input
            )
            await self._broadcast_node(session_id, answer_node, db)
            await self._broadcast_edge(session_id, answer_edge, db)

        # Save user message
        await session_manager.add_message(
            db, session_id, role="user", content=user_input
        )

        # Build message history for Claude
        messages = await self._build_messages(db, session_id)

        # Call Claude
        response = await claude_client.create_message(
            system=mode.system_prompt,
            messages=messages,
            tools=CONVERSATION_TOOLS,
        )

        return await self._process_response(db, session_id, response)

    async def resume_session(
        self, db: AsyncSession, session_id: str
    ) -> ConversationResponse:
        """Resume a paused session with context restoration."""
        session = await session_manager.get(db, session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        mode = get_mode(session.mode_id)
        state = await diagram_engine.get_full_state(db, session_id)

        # Build resume context
        resume_content = RESUME_PROMPT_TEMPLATE.format(
            context_summary=session.context_summary or "No summary available",
            node_count=len(state.nodes),
            edge_count=len(state.edges),
            last_category="unknown",
        )

        # Add resume message to history
        await session_manager.add_message(
            db, session_id, role="user", content="I'd like to resume this session."
        )

        messages = await self._build_messages(db, session_id)
        # Inject resume context as system-like user message
        messages.insert(0, {"role": "user", "content": resume_content})
        messages.insert(1, {"role": "assistant", "content": "I understand. Let me review where we left off."})

        # Update session status
        await session_manager.update(db, session_id, status="active")

        response = await claude_client.create_message(
            system=mode.system_prompt,
            messages=messages,
            tools=CONVERSATION_TOOLS,
        )

        # Broadcast full diagram sync
        await ws_manager.broadcast(
            session_id,
            DiagramEvent(
                type="full_sync",
                metadata={
                    "nodes": [n.model_dump(mode="json") for n in state.nodes],
                    "edges": [e.model_dump(mode="json") for e in state.edges],
                },
            ).model_dump(mode="json"),
        )

        return await self._process_response(db, session_id, response)

    async def _process_response(
        self,
        db: AsyncSession,
        session_id: str,
        response: Any,
        is_initial: bool = False,
    ) -> ConversationResponse:
        """Process Claude's response: extract text, handle tool calls."""
        assistant_text = ""
        question_data = None
        diagram_update_count = 0
        last_question_node_id = None

        # Handle multi-turn tool use
        current_response = response
        tool_results = []

        while True:
            for block in current_response.content:
                if block.type == "text":
                    assistant_text += block.text

                elif block.type == "tool_use":
                    result = await self._handle_tool_call(
                        db, session_id, block.name, block.input
                    )

                    if block.name == "ask_question":
                        question_data = block.input
                        last_question_node_id = result.get("node_id")
                        diagram_update_count += 1

                    elif block.name == "update_diagram":
                        diagram_update_count += result.get("update_count", 0)

                    elif block.name == "conclude_section":
                        diagram_update_count += 1

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                    })

            # If Claude wants to continue with more tool calls
            if current_response.stop_reason == "tool_use" and tool_results:
                messages = await self._build_messages(db, session_id)
                if not is_initial:
                    pass  # messages already include history
                else:
                    messages = [
                        {
                            "role": "user",
                            "content": "Please start the consultation.",
                        }
                    ]

                # Add assistant response with tool uses
                messages.append({
                    "role": "assistant",
                    "content": current_response.content,
                })
                # Add tool results
                messages.append({
                    "role": "user",
                    "content": tool_results,
                })

                tool_results = []
                mode = get_mode(
                    (await session_manager.get(db, session_id)).mode_id
                )
                current_response = await claude_client.create_message(
                    system=mode.system_prompt,
                    messages=messages,
                    tools=CONVERSATION_TOOLS,
                )
                continue

            break

        # Update current node pointer
        if last_question_node_id:
            await session_manager.update(
                db, session_id, current_node_id=last_question_node_id
            )

        # Save assistant message
        msg = await session_manager.add_message(
            db,
            session_id,
            role="assistant",
            content=assistant_text,
            structured_data=question_data,
            node_id=last_question_node_id,
        )

        question = None
        if question_data:
            question = QuestionData(
                question_text=question_data["question_text"],
                question_type=question_data["question_type"],
                choices=question_data.get("choices", []),
                category=question_data["category"],
                reasoning=question_data["reasoning"],
            )

        return ConversationResponse(
            message=MessageResponse(
                id=msg.id,
                session_id=msg.session_id,
                sequence=msg.sequence,
                role=msg.role,
                content=msg.content,
                structured_data=msg.structured_data,
                node_id=msg.node_id,
                created_at=msg.created_at,
            ),
            question=question,
            diagram_updates=diagram_update_count,
        )

    async def _handle_tool_call(
        self,
        db: AsyncSession,
        session_id: str,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle a tool call from Claude."""
        session = await session_manager.get(db, session_id)

        if tool_name == "ask_question":
            node, edge = await diagram_engine.add_question_node(
                db,
                session_id,
                tool_input,
                parent_node_id=session.current_node_id if session else None,
            )
            await self._broadcast_node(session_id, node, db)
            if edge:
                await self._broadcast_edge(session_id, edge, db)
            return {"status": "question_presented", "node_id": node.id}

        elif tool_name == "update_diagram":
            events = await diagram_engine.apply_updates(
                db, session_id, tool_input
            )
            for event in events:
                await ws_manager.broadcast(session_id, event)
            return {"status": "diagram_updated", "update_count": len(events)}

        elif tool_name == "do_research":
            # For MVP: acknowledge research need, actual search can be added later
            logger.info(f"Research requested: {tool_input['topic']}")
            return {
                "status": "research_noted",
                "note": f"Research on '{tool_input['topic']}' acknowledged. "
                "Using existing knowledge for now.",
            }

        elif tool_name == "conclude_section":
            node = await diagram_engine.add_summary_node(
                db,
                session_id,
                tool_input,
                parent_node_id=session.current_node_id if session else None,
            )
            await self._broadcast_node(session_id, node, db)
            await ws_manager.broadcast(
                session_id,
                DiagramEvent(
                    type="section_complete",
                    metadata={
                        "section": tool_input["section_name"],
                        "next": tool_input.get("next_section"),
                    },
                ).model_dump(mode="json"),
            )
            return {
                "status": "section_concluded",
                "node_id": node.id,
            }

        return {"status": "unknown_tool", "tool": tool_name}

    async def _build_messages(
        self, db: AsyncSession, session_id: str
    ) -> list[dict[str, Any]]:
        """Build the messages array from conversation history."""
        db_messages = await session_manager.get_messages(db, session_id)
        messages = []
        for msg in db_messages:
            messages.append({
                "role": msg.role,
                "content": msg.content,
            })
        return messages

    async def _broadcast_node(
        self, session_id: str, node: Any, db: AsyncSession
    ):
        """Broadcast a node addition via WebSocket."""
        await ws_manager.broadcast(
            session_id,
            DiagramEvent(
                type="node_added",
                node=DiagramNodeSchema(
                    id=node.id,
                    session_id=node.session_id,
                    node_type=node.node_type,
                    label=node.label,
                    description=node.description,
                    status=node.status,
                    metadata=node.metadata_,
                    position_x=node.position_x,
                    position_y=node.position_y,
                    created_at=node.created_at,
                ),
            ).model_dump(mode="json"),
        )

    async def _broadcast_edge(
        self, session_id: str, edge: Any, db: AsyncSession
    ):
        """Broadcast an edge addition via WebSocket."""
        await ws_manager.broadcast(
            session_id,
            DiagramEvent(
                type="edge_added",
                edge=DiagramEdgeSchema(
                    id=edge.id,
                    session_id=edge.session_id,
                    source_node_id=edge.source_node_id,
                    target_node_id=edge.target_node_id,
                    label=edge.label,
                    edge_type=edge.edge_type,
                    is_taken=edge.is_taken,
                    created_at=edge.created_at,
                ),
            ).model_dump(mode="json"),
        )


conversation_engine = ConversationEngine()
