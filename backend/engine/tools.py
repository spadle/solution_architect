CONVERSATION_TOOLS = [
    {
        "name": "ask_question",
        "description": (
            "Ask the user a structured question to gather requirements. "
            "Use this for every question you pose to the user."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "question_text": {
                    "type": "string",
                    "description": "The question to ask the user",
                },
                "question_type": {
                    "type": "string",
                    "enum": [
                        "single_choice",
                        "multiple_choice",
                        "free_text",
                        "yes_no",
                        "scale",
                    ],
                    "description": "The type of answer expected",
                },
                "choices": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Available choices for choice-type questions",
                },
                "category": {
                    "type": "string",
                    "description": "Domain category of this question",
                },
                "reasoning": {
                    "type": "string",
                    "description": "Why this question matters for the solution design",
                },
            },
            "required": [
                "question_text",
                "question_type",
                "category",
                "reasoning",
            ],
        },
    },
    {
        "name": "update_diagram",
        "description": (
            "Add nodes and edges to the solution diagram based on conversation progress. "
            "Call this after gathering information to visualize the decision tree."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "nodes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "temp_id": {
                                "type": "string",
                                "description": "Temporary ID for referencing in edges",
                            },
                            "node_type": {
                                "type": "string",
                                "enum": [
                                    "question",
                                    "decision",
                                    "answer",
                                    "info",
                                    "research",
                                    "summary",
                                ],
                            },
                            "label": {
                                "type": "string",
                                "description": "Short display label for the node",
                            },
                            "description": {
                                "type": "string",
                                "description": "Detailed description",
                            },
                        },
                        "required": ["temp_id", "node_type", "label"],
                    },
                },
                "edges": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source_id": {
                                "type": "string",
                                "description": "Source node temp_id or existing node ID",
                            },
                            "target_id": {
                                "type": "string",
                                "description": "Target node temp_id or existing node ID",
                            },
                            "label": {"type": "string"},
                            "edge_type": {
                                "type": "string",
                                "enum": ["flow", "decision", "skip", "research"],
                            },
                        },
                        "required": ["source_id", "target_id"],
                    },
                },
            },
            "required": ["nodes", "edges"],
        },
    },
    {
        "name": "do_research",
        "description": (
            "Signal that domain research is needed before continuing the consultation. "
            "Use when you need to verify technology claims, find alternatives, or gather domain knowledge."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "What to research",
                },
                "reason": {
                    "type": "string",
                    "description": "Why this research is needed",
                },
                "search_queries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Suggested search queries",
                },
            },
            "required": ["topic", "reason"],
        },
    },
    {
        "name": "conclude_section",
        "description": (
            "Mark a consultation section as complete and summarize the key findings. "
            "Use after completing a category of questions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "section_name": {"type": "string"},
                "summary": {
                    "type": "string",
                    "description": "Summary of findings in this section",
                },
                "key_decisions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of key decisions made",
                },
                "next_section": {
                    "type": "string",
                    "description": "What section comes next",
                },
            },
            "required": ["section_name", "summary", "key_decisions"],
        },
    },
]
