"""LLM client for question generation via OpenRouter API."""

from __future__ import annotations

import json
import logging
import os
import urllib.request
import urllib.error

# Load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

OPENROUTER_URL = os.environ.get("OPENROUTER_URL", "https://openrouter.ai/api/v1/chat/completions")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
MODEL = os.environ.get("LLM_MODEL", "openrouter/free")
FALLBACK_MODELS = [
    "google/gemma-3-27b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "nvidia/nemotron-nano-9b-v2:free",
]

# Language directives appended to system prompts
LANGUAGE_DIRECTIVES = {
    "en": "",
    "ko": "\n\nIMPORTANT: Generate ALL text content (question, choices, category, reasoning) in Korean (한국어). Do NOT use English for any user-facing text. Category names should also be in Korean.",
}


def _call_llm(messages: list[dict], temperature: float = 0.7) -> str:
    """Call OpenRouter chat API with automatic fallback to alternative models."""
    models_to_try = [MODEL] + FALLBACK_MODELS

    for model in models_to_try:
        result = _call_openrouter(model, messages, temperature)
        if result:
            return result
        logger.info(f"Model {model} failed, trying next fallback...")

    logger.error("All models failed")
    return ""


import time


def _call_openrouter(model: str, messages: list[dict], temperature: float) -> str:
    """Call a single OpenRouter model with retry on 429/5xx errors."""
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 4096,
        "provider": {
            "data_collection": "allow",
            "allow_fallbacks": True,
        },
    }).encode("utf-8")

    max_retries = 3
    for attempt in range(max_retries):
        req = urllib.request.Request(
            OPENROUTER_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://solution-architect.app",
                "X-Title": "Solution Architect",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=55) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                msg = data.get("choices", [{}])[0].get("message", {})
                content = msg.get("content", "") or ""
                # Some models return reasoning instead of content
                if not content.strip():
                    content = msg.get("reasoning", "") or ""
                content = _strip_thinking(content)
                return content.strip()
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if e.fp else ""
            logger.warning(f"OpenRouter {model} HTTP {e.code} (attempt {attempt+1}): {body[:200]}")
            # Retry on 429 (rate limit) or 5xx (server error)
            if e.code in (429, 500, 502, 503) and attempt < max_retries - 1:
                wait = (attempt + 1) * 2
                logger.info(f"Retrying {model} in {wait}s...")
                time.sleep(wait)
                continue
            return ""
        except urllib.error.URLError as e:
            logger.error(f"OpenRouter connection failed (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return ""
        except Exception as e:
            logger.error(f"OpenRouter error: {e}")
            return ""
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
    q = obj.get("question", "").strip().lower()
    return q in ("...", "", "the question text to ask the user",
                 "what is your preferred wedding venue type?")


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

You MUST respond with ONLY a JSON object. Here is an example for a wedding planning consultation:

{
  "question": "What is your preferred wedding venue type?",
  "choices": ["Indoor banquet hall", "Outdoor garden", "Beach ceremony", "Church or chapel", "Other (specify)"],
  "category": "venue",
  "reasoning": "The venue type determines catering options, guest capacity, and weather contingencies"
}

IMPORTANT: The choices must be FULL DESCRIPTIVE TEXT, not single letters. Each choice should be a complete phrase that clearly describes the option.

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
    q_count = len(qa_history)

    lang_directive = LANGUAGE_DIRECTIVES.get(language, "")
    messages = [{"role": "system", "content": QUESTION_GEN_SYSTEM + lang_directive}]

    # Build context from history — use last 12 Q&As to avoid context overflow
    context_parts = [f"Topic: {topic}", f"Mode: {mode_context}"]
    recent_qa = qa_history[-12:] if len(qa_history) > 12 else qa_history
    if recent_qa:
        # Include categories covered from full history so LLM explores new areas
        all_categories = [qa.get("category", "") for qa in qa_history if qa.get("category")]
        if all_categories:
            context_parts.append(f"\nCategories already covered: {', '.join(set(all_categories))}")
        context_parts.append(f"\nPrevious Q&A ({q_count} total, showing recent):")
        for qa in recent_qa:
            context_parts.append(f"Q: {qa['question']}")
            context_parts.append(f"A: {qa['answer']}")

    if q_count < 8:
        areas_hint = "\nYou have only asked {0} question(s). You MUST continue asking. Areas to explore: requirements, constraints, scale, technology, security, budget, timeline, integrations, user experience, deployment.".format(q_count)
    else:
        areas_hint = ""

    context_parts.append(
        f"\n{q_count} questions asked so far.{areas_hint}\n"
        "Generate the NEXT question about a NEW uncovered area. Respond with ONLY a JSON object, no other text."
    )

    messages.append({"role": "user", "content": "\n".join(context_parts)})

    # Retry up to 5 times with decreasing temperature
    temps = [0.7, 0.5, 0.3, 0.3, 0.2]
    for attempt in range(5):
        temp = temps[attempt]
        # On retries, add explicit JSON reminder to user message
        if attempt > 0:
            retry_messages = messages.copy()
            retry_messages.append({
                "role": "assistant", "content": '{"question": "'
            })
            response = '{"question": "' + _call_llm(retry_messages, temperature=temp)
        else:
            response = _call_llm(messages, temperature=temp)
        print(f"[QGen] attempt={attempt} t={temp} q_count={q_count} len={len(response)} first200={response[:200]}", flush=True)
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

        # Reject duplicate questions (fuzzy + keyword overlap)
        q_lower = q_text.lower().strip()
        # Extract key words (3+ chars) for overlap check
        q_words = set(w for w in re.findall(r'\w{3,}', q_lower) if w not in (
            'the', 'and', 'for', 'are', 'how', 'what', 'which', 'your', 'you',
            'this', 'that', 'with', 'from', 'have', 'will', 'about', 'would',
            'does', 'any', 'etc', 'specify', 'other', 'prefer',
        ))
        is_dup = False
        for prev in qa_history:
            prev_q = prev.get("question", "").lower().strip()
            # Exact or prefix match
            if q_lower == prev_q or (len(q_lower) > 20 and q_lower[:40] == prev_q[:40]):
                is_dup = True
                break
            # Keyword overlap: if 60%+ of key words match, likely duplicate
            prev_words = set(w for w in re.findall(r'\w{3,}', prev_q) if w not in (
                'the', 'and', 'for', 'are', 'how', 'what', 'which', 'your', 'you',
                'this', 'that', 'with', 'from', 'have', 'will', 'about', 'would',
                'does', 'any', 'etc', 'specify', 'other', 'prefer',
            ))
            if q_words and prev_words:
                overlap = len(q_words & prev_words) / min(len(q_words), len(prev_words))
                if overlap >= 0.6:
                    is_dup = True
                    break
        if is_dup:
            print(f"[QGen] Duplicate question detected, retrying: {q_text[:60]}", flush=True)
            continue

        # Ensure choices exist and are real
        choices = parsed.get("choices", [])
        # Strip "A) " or "1. " prefixes that some models add
        cleaned_choices = []
        for c in choices:
            c = c.strip()
            # Remove letter/number prefixes like "A) ", "A. ", "1. ", "1) "
            c = re.sub(r'^[A-Da-d1-5][\.\)]\s*', '', c).strip()
            cleaned_choices.append(c)
        choices = cleaned_choices
        # Filter out placeholders, single letters, and empty strings
        placeholder_set = {"...", "choice a", "choice b", "choice c", "choice d",
                          "a", "b", "c", "d", "option a", "option b", "option c",
                          "the question text to ask the user", ""}
        choices = [c for c in choices if c.strip().lower() not in placeholder_set and len(c.strip()) > 1]
        if not choices:
            if language == "ko":
                choices = ["예", "아니오", "기타 (직접 입력)"]
            else:
                choices = ["Yes", "No", "Other (specify)"]

        # Add "Other" option if missing — use language-appropriate text
        other_keywords = ("other", "기타", "직접", "specify")
        has_other = any(any(kw in c.lower() for kw in other_keywords) for c in choices)
        if not has_other:
            choices.append("기타 (직접 입력)" if language == "ko" else "Other (specify)")

        return {
            "question": q_text,
            "choices": choices,
            "category": parsed.get("category", "general"),
            "reasoning": parsed.get("reasoning", ""),
        }

    # Last resort: if we're early in the consultation, try a minimal prompt
    if q_count < 8:
        print(f"[QGen] All 5 attempts failed, trying minimal fallback (q_count={q_count})", flush=True)
        fallback_prompt = (
            f"Topic: {topic}\nAsk ONE clarifying question about this topic. "
            f"Return ONLY JSON: {{\"question\": \"...\", \"choices\": [\"opt1\", \"opt2\", \"opt3\", \"Other (specify)\"], \"category\": \"general\", \"reasoning\": \"...\"}}"
        )
        response = _call_llm([{"role": "user", "content": fallback_prompt}], temperature=0.5)
        if response:
            parsed = _parse_json_from_response(response)
            if parsed and parsed.get("question") and len(parsed["question"]) > 5:
                choices = parsed.get("choices", ["Yes", "No", "Other (specify)"])
                choices = [c for c in choices if len(c.strip()) > 1]
                if not choices:
                    choices = ["Yes", "No", "Other (specify)"]
                return {
                    "question": parsed["question"],
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
    response = _call_llm(messages, temperature=0.3)
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
    response = _call_llm(messages, temperature=0.3)
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

    response = _call_llm(messages, temperature=0.3)
    if not response:
        return None

    return _parse_json_from_response(response)


DOC_SYSTEM_TEMPLATES = {
    "architecture": """You are a solution architect. Based on the consultation Q&A below, generate a system architecture document.

Include these sections:
1. **System Overview** — High-level description and goals
2. **Architecture Diagram Description** — Components and their interactions (describe in text)
3. **Technology Stack** — Recommended technologies with justification
4. **Data Flow** — How data moves through the system
5. **Key Design Decisions** — Major architectural choices and trade-offs
6. **Scalability Considerations** — How the system handles growth
7. **Security Architecture** — Authentication, authorization, data protection

Format using markdown. Be specific and actionable based on the consultation answers.""",

    "documentation": """You are a technical writer. Based on the consultation Q&A below, generate comprehensive project documentation.

Include these sections:
1. **Project Overview** — Purpose, scope, and objectives
2. **Requirements Summary** — Functional and non-functional requirements
3. **System Components** — Detailed description of each component
4. **Integration Points** — External systems and APIs
5. **Deployment Strategy** — Infrastructure and deployment approach
6. **Risk Assessment** — Identified risks and mitigations
7. **Timeline & Milestones** — Suggested project phases
8. **Success Criteria** — How to measure project success

Format using markdown. Be thorough and reference specific answers from the consultation.""",
}


def generate_doc(
    topic: str,
    qa_history: list[dict],
    doc_type: str = "architecture",
    language: str = "en",
) -> str:
    """Generate architecture or documentation from consultation Q&A."""
    system_prompt = DOC_SYSTEM_TEMPLATES.get(doc_type, DOC_SYSTEM_TEMPLATES["architecture"])
    lang_directive = LANGUAGE_DIRECTIVES.get(language, "")

    messages = [{"role": "system", "content": system_prompt + lang_directive}]

    context_parts = [f"Topic: {topic}", "\nConsultation Q&A:"]
    for qa in qa_history:
        context_parts.append(f"Q: {qa['question']}")
        context_parts.append(f"A: {qa['answer']}")

    context_parts.append(f"\nGenerate the {'system architecture' if doc_type == 'architecture' else 'project documentation'} based on the above consultation.")
    messages.append({"role": "user", "content": "\n".join(context_parts)})

    response = _call_llm(messages, temperature=0.4)
    return response or ""
