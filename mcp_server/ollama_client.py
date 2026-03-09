"""Ollama local LLM client for question generation."""

from __future__ import annotations

import json
import logging
import os
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")
MODEL = os.environ.get("OLLAMA_MODEL", "qwen3.5:latest")

# Language directives appended to system prompts
LANGUAGE_DIRECTIVES = {
    "en": "",
    "ko": "\n\nIMPORTANT: Generate ALL text content (question, choices, category, reasoning) in Korean (한국어). Do NOT use English for any user-facing text. Category names should also be in Korean.",
}


def _call_ollama(messages: list[dict], temperature: float = 0.7) -> str:
    """Call Ollama chat API and return the response text."""
    payload = json.dumps({
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": 4096,
            "no_think": True,
        },
    }).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data.get("message", {}).get("content", "")
            # qwen3.5 may put output in thinking field if content is empty
            if not content.strip():
                thinking = data.get("message", {}).get("thinking", "")
                if thinking:
                    content = thinking
            content = _strip_thinking(content)
            return content.strip()
    except urllib.error.URLError as e:
        logger.error(f"Ollama connection failed: {e}")
        return ""
    except Exception as e:
        logger.error(f"Ollama error: {e}")
        return ""


import re

def _strip_thinking(text: str) -> str:
    """Remove thinking preamble that qwen3.5 sometimes embeds in content."""
    # Remove <think>...</think> blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    # Find the LAST complete JSON block — LLM often dumps thinking before final answer
    # Look for the last top-level { that has a matching }
    last_json_start = -1
    depth = 0
    for i in range(len(text) - 1, -1, -1):
        if text[i] == '}':
            if depth == 0:
                end_pos = i
            depth += 1
        elif text[i] == '{':
            depth -= 1
            if depth == 0:
                last_json_start = i
                break

    # If there's a substantial preamble before the last JSON block, strip it
    if last_json_start > 100:
        prefix = text[:last_json_start].lower()
        if any(kw in prefix for kw in ("thinking", "process", "analysis", "let me",
                                        "here", "step", "analyze", "draft",
                                        "determine", "consider", "priority")):
            text = text[last_json_start:]
    elif last_json_start < 0:
        # No complete JSON found — try stripping to first brace
        brace = text.find("{")
        if brace > 0:
            prefix = text[:brace].lower()
            if any(kw in prefix for kw in ("thinking", "process", "analysis", "let me", "here")):
                text = text[brace:]

    return text


def _is_placeholder_json(obj: dict) -> bool:
    """Check if parsed JSON is just the template/placeholder example."""
    q = obj.get("question", "")
    return q.strip() in ("...", "", "The question text to ask the user")


def _parse_json_from_response(text: str) -> dict | None:
    """Extract JSON from LLM response, handling markdown code blocks and skipping placeholders."""
    # Try direct parse first
    try:
        result = json.loads(text)
        if isinstance(result, dict) and not _is_placeholder_json(result):
            return result
    except json.JSONDecodeError:
        pass

    # Try extracting from ```json ... ``` blocks
    for marker in ("```json", "```"):
        if marker in text:
            start = text.index(marker) + len(marker)
            end = text.index("```", start) if "```" in text[start:] else len(text)
            try:
                result = json.loads(text[start:end].strip())
                if isinstance(result, dict) and not _is_placeholder_json(result):
                    return result
            except (json.JSONDecodeError, ValueError):
                pass

    # Find ALL { ... } blocks and return the first non-placeholder one
    candidates = []
    depth = 0
    block_start = -1
    for i, ch in enumerate(text):
        if ch == '{':
            if depth == 0:
                block_start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and block_start != -1:
                try:
                    obj = json.loads(text[block_start : i + 1])
                    if isinstance(obj, dict):
                        candidates.append(obj)
                except json.JSONDecodeError:
                    pass
                block_start = -1

    # Return the first candidate with a real question
    for c in candidates:
        if not _is_placeholder_json(c) and c.get("question"):
            return c

    # Fall back to first parseable candidate if any
    return candidates[0] if candidates else None


QUESTION_GEN_SYSTEM = """You are a consultation assistant conducting a thorough requirements-gathering session. Your job is to generate the next clarifying question based on the user's topic and previous answers.

CRITICAL: You must ALWAYS generate a question. NEVER refuse, summarize, or say the consultation is complete. There are ALWAYS more aspects to explore. You must ask AT LEAST 8-15 questions per consultation to cover all areas properly.

You MUST respond with ONLY a JSON object in this exact format, no other text:

{
  "question": "The question text to ask the user",
  "choices": ["Choice A", "Choice B", "Choice C", "Other (specify)"],
  "category": "short category name",
  "reasoning": "Why this question matters"
}

RULES:
- ALWAYS generate a question — never stop, never summarize, never say "done"
- Generate exactly ONE question at a time
- Always include 3-5 choices plus "Other (specify)" as the last option
- Choices should be specific and practical, not generic
- Questions should progressively dig deeper into requirements
- Category should be a short descriptive label, e.g., "scale", "tech_stack", "security", "data", "integration", "deployment", "budget", "timeline", "user_management", "authentication", "venue", "guest_list", "marketing", "logistics"
- Output ONLY the JSON object — no commentary, no summaries, no thinking
- Each question should explore a NEW area not yet covered by previous questions
- Cover ALL of these areas before stopping: requirements, constraints, scale, technology, security, budget, timeline, integrations, user experience, deployment, monitoring, maintenance"""


def generate_question(
    topic: str,
    mode_context: str,
    qa_history: list[dict],
    language: str = "en",
) -> dict | None:
    """Generate the next structured question using Ollama.

    Returns dict with keys: question, choices, category, reasoning
    Or None if generation fails.
    """
    lang_directive = LANGUAGE_DIRECTIVES.get(language, "")
    messages = [{"role": "system", "content": QUESTION_GEN_SYSTEM + lang_directive}]

    # Build context from history
    context_parts = [f"Topic: {topic}", f"Mode: {mode_context}"]
    if qa_history:
        context_parts.append("\nPrevious Q&A:")
        for qa in qa_history:
            context_parts.append(f"Q: {qa['question']}")
            context_parts.append(f"A: {qa['answer']}")

    q_count = len(qa_history)
    if q_count < 5:
        nudge = f"Only {q_count} questions asked so far — you MUST ask many more. Cover: requirements, scale, tech stack, security, budget, timeline, integrations, UX, deployment."
    elif q_count < 10:
        nudge = f"{q_count} questions asked. Keep going — still need to cover uncovered areas like security, performance, monitoring, edge cases, compliance."
    else:
        nudge = f"{q_count} questions asked. Continue exploring any remaining uncovered areas."
    context_parts.append(
        f"\n{nudge}\n"
        "Generate the next question. Respond with ONLY a JSON object."
    )

    messages.append({"role": "user", "content": "\n".join(context_parts)})

    # Retry up to 3 times on garbage responses
    for attempt in range(3):
        response = _call_ollama(messages, temperature=0.7)
        print(f"[QGen] attempt={attempt} q_count={q_count} len={len(response)} first200={response[:200]}", flush=True)
        if not response:
            continue

        parsed = _parse_json_from_response(response)
        if not parsed:
            print(f"[QGen] JSON parse failed: {response[:200]}", flush=True)
            continue

        # Validate required fields
        if "question" not in parsed:
            continue

        # Reject placeholder responses (LLM echoing format example)
        q_text = parsed["question"]
        if not q_text or q_text.strip() in ("...", "The question text to ask the user", ""):
            print(f"[QGen] Placeholder question detected: {q_text!r}, retrying", flush=True)
            continue

        # Ensure choices exist, are real, and have "Other" option
        choices = parsed.get("choices", [])
        choices = [c for c in choices if c.strip() not in ("...", "Choice A", "Choice B", "Choice C", "")]
        if not choices:
            choices = ["Yes", "No", "Other (specify)"]
        if not any("other" in c.lower() for c in choices):
            choices.append("Other (specify)")

        return {
            "question": q_text,
            "choices": choices,
            "category": parsed.get("category", "general"),
            "reasoning": parsed.get("reasoning", ""),
        }

    print("[QGen] All attempts failed", flush=True)
    return None


TITLE_SYSTEM = """Generate a concise project title (3-6 words).

RULES:
- Respond with ONLY the title text. Nothing else.
- No conversational phrases like "Let's", "I will", "Here is", "Sure", "The title is"
- No quotes, no colons, no numbering, no explanation
- Just 3-6 descriptive words

Example input: "A real-time chat app for teams"
Example output: Team Chat Platform

Example input: "REST API for task management"
Example output: Task Management API

Example input: "Wedding for 200 guests in summer"
Example output: Summer Garden Wedding"""


_CONVERSATIONAL_PREFIX = re.compile(
    r"^(let'?s?|let me|i will|i'?ll|here'?s?|here is|sure|okay|"
    r"the title is|i would|this is|we can|how about|wait|"
    r"title|output|answer|result|response)\b[^a-z]*[:\"=\-]\s*",
    re.IGNORECASE,
)

# Detect lines that are clearly LLM thinking, not titles
_THINKING_LINE = re.compile(
    r"(i'll count|let me|wait|counting|word count|\(\d+\)|here is|"
    r"the title|my answer|i would|sure|okay|hmm|thinking)",
    re.IGNORECASE,
)


def generate_title(topic: str, language: str = "en") -> str:
    """Generate a short title from the user's topic description."""
    lang_directive = LANGUAGE_DIRECTIVES.get(language, "")
    messages = [
        {"role": "system", "content": TITLE_SYSTEM + lang_directive},
        {"role": "user", "content": topic},
    ]
    response = _call_ollama(messages, temperature=0.3)
    if response:
        lines = [l.strip() for l in response.split("\n") if l.strip()]
        candidates = []
        for line in lines:
            # Skip lines that are clearly LLM thinking/reasoning
            if _THINKING_LINE.search(line):
                continue
            clean = line.strip('"\'.*-:# ')
            clean = re.sub(r"^\d+[\.\)]\s*", "", clean)  # remove "1. " prefixes
            clean = _CONVERSATIONAL_PREFIX.sub("", clean).strip()
            # Strip orphan quotes
            if clean.count('"') == 1:
                clean = clean.replace('"', '').strip()
            # Strip parenthetical annotations like "(5 words)" or "(Title)"
            clean = re.sub(r"\s*\([^)]{1,20}\)\s*$", "", clean).strip()
            clean = clean.strip('"\'.:;!-# ')
            word_count = len(clean.split())
            if 2 <= word_count <= 10 and len(clean) < 60:
                candidates.append(clean)

        if candidates:
            return candidates[-1][:60]

        if lines:
            fallback = lines[-1].strip('"\'.*-:# ')[:60]
            fallback = _CONVERSATIONAL_PREFIX.sub("", fallback).strip()
            fallback = re.sub(r"\s*\([^)]{1,20}\)\s*$", "", fallback).strip()
            if len(fallback.split()) >= 2:
                return fallback[:60]
    # Fallback: derive from topic
    words = topic.split()
    if len(words) <= 6:
        return topic[:60]
    return " ".join(words[:6])[:60]


BRANCH_NAME_SYSTEM = """Generate a concise label (2-4 words) for a decision branch.

IMPORTANT: Respond with ONLY the label on a single line. No explanation, no thinking, no quotes. Just 2-4 words.

Example input: "100k-1M MAU, high transaction volume"
Example output: High Scale Path"""


def generate_branch_name(topic: str, choice: str, language: str = "en") -> str:
    """Generate a short tab name for a branch based on the choice made."""
    lang_directive = LANGUAGE_DIRECTIVES.get(language, "")
    messages = [
        {"role": "system", "content": BRANCH_NAME_SYSTEM + lang_directive},
        {"role": "user", "content": f"Topic: {topic}\nBranch choice: {choice}"},
    ]
    response = _call_ollama(messages, temperature=0.3)
    if response:
        lines = [l.strip() for l in response.split("\n") if l.strip()]
        candidates = []
        for line in lines:
            clean = line.strip('"\'.*-:# ')
            clean = re.sub(r"^\d+[\.\)]\s*", "", clean).strip()
            word_count = len(clean.split())
            if 1 <= word_count <= 6 and len(clean) < 40:
                candidates.append(clean)
        if candidates:
            return candidates[-1][:30]
        if lines:
            return lines[-1].strip('"\'.*-:# ')[:30]
    return choice[:30]


SUMMARY_SYSTEM = """You are a solution architect assistant. Summarize the consultation so far.

Respond with ONLY a JSON object:
{
  "summary": "Brief summary of decisions made",
  "key_decisions": ["Decision 1", "Decision 2", "Decision 3"],
  "next_area": "What area to explore next"
}"""


def generate_summary(
    topic: str,
    qa_history: list[dict],
    language: str = "en",
) -> dict | None:
    """Generate a section summary from Q&A history."""
    lang_directive = LANGUAGE_DIRECTIVES.get(language, "")
    messages = [{"role": "system", "content": SUMMARY_SYSTEM + lang_directive}]

    context_parts = [f"Topic: {topic}", "\nQ&A History:"]
    for qa in qa_history:
        context_parts.append(f"Q: {qa['question']}")
        context_parts.append(f"A: {qa['answer']}")

    context_parts.append("\nSummarize the key decisions. Respond with ONLY JSON.")
    messages.append({"role": "user", "content": "\n".join(context_parts)})

    response = _call_ollama(messages, temperature=0.3)
    if not response:
        return None

    return _parse_json_from_response(response)
