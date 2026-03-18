"""LLM client — NVIDIA Nemotron 3 Super (primary) with OpenRouter fallback."""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
import urllib.error

# Load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

# ── NVIDIA direct API ────────────────────────────────────────────────────
NVIDIA_URL = os.environ.get("NVIDIA_URL", "https://integrate.api.nvidia.com/v1/chat/completions")
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
NVIDIA_MODEL = os.environ.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b")

# ── OpenRouter fallback ──────────────────────────────────────────────────
OPENROUTER_URL = os.environ.get("OPENROUTER_URL", "https://openrouter.ai/api/v1/chat/completions")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
FALLBACK_MODELS = [
    "openrouter/free",
    "google/gemma-3-27b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
]

# Language directives appended to system prompts
LANGUAGE_DIRECTIVES = {
    "en": "",
    "ko": "\n\nIMPORTANT: Generate ALL text content (question, choices, category, reasoning) in Korean (한국어). Do NOT use English for any user-facing text. Category names should also be in Korean.",
}


def _call_llm(messages: list[dict], temperature: float = 0.7) -> str:
    """Try NVIDIA Nemotron direct, then fall back to OpenRouter models."""
    # 1. Try NVIDIA direct API first
    if NVIDIA_API_KEY:
        result = _call_nvidia(messages, temperature)
        if result:
            return result
        logger.info("NVIDIA API failed, falling back to OpenRouter...")

    # 2. OpenRouter fallback chain
    for model in FALLBACK_MODELS:
        result = _call_openrouter(model, messages, temperature)
        if result:
            return result
        logger.info(f"OpenRouter {model} failed, trying next...")

    logger.error("All models failed")
    return ""


def _call_nvidia(messages: list[dict], temperature: float) -> str:
    """Call NVIDIA Nemotron 3 Super directly via integrate.api.nvidia.com."""
    payload = json.dumps({
        "model": NVIDIA_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 4096,
        "top_p": 0.95,
    }).encode("utf-8")

    max_retries = 2
    for attempt in range(max_retries):
        req = urllib.request.Request(
            NVIDIA_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {NVIDIA_API_KEY}",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=55) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                msg = data.get("choices", [{}])[0].get("message", {})
                content = msg.get("content", "") or ""
                # Nemotron may return reasoning_content separately
                if not content.strip():
                    content = msg.get("reasoning_content", "") or msg.get("reasoning", "") or ""
                content = _strip_thinking(content)
                if content.strip():
                    logger.info(f"NVIDIA Nemotron OK (len={len(content)})")
                    return content.strip()
                return ""
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if e.fp else ""
            logger.warning(f"NVIDIA HTTP {e.code} (attempt {attempt+1}): {body[:200]}")
            if e.code in (429, 500, 502, 503) and attempt < max_retries - 1:
                time.sleep((attempt + 1) * 2)
                continue
            return ""
        except urllib.error.URLError as e:
            logger.error(f"NVIDIA connection failed (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return ""
        except Exception as e:
            logger.error(f"NVIDIA error: {e}")
            return ""
    return ""


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
                if not content.strip():
                    content = msg.get("reasoning", "") or ""
                content = _strip_thinking(content)
                return content.strip()
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if e.fp else ""
            logger.warning(f"OpenRouter {model} HTTP {e.code} (attempt {attempt+1}): {body[:200]}")
            if e.code in (429, 500, 502, 503) and attempt < max_retries - 1:
                time.sleep((attempt + 1) * 2)
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
    # ── Software / Tech modes ────────────────────────────────
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

    # ── Wedding Planner ──────────────────────────────────────
    "wedding_plan": """You are an experienced wedding planner. Based on the consultation Q&A below, generate a comprehensive wedding plan.

Include these sections:
1. **Wedding Overview** — Theme, style, and overall vision
2. **Budget Breakdown** — Estimated allocation per category (venue, catering, attire, photography, flowers, music, decor, etc.) with percentages
3. **Venue & Date** — Recommended venue type, layout considerations, date/season notes
4. **Guest Experience** — Ceremony flow, reception plan, seating considerations
5. **Vendor Checklist** — List of vendors needed with priority and estimated costs
6. **Day-of Timeline** — Hour-by-hour schedule from preparation to send-off
7. **Planning Milestones** — Month-by-month countdown checklist

Format using markdown. Be specific based on the couple's answers.""",

    "wedding_budget": """You are a wedding budget specialist. Based on the consultation Q&A below, generate a detailed budget breakdown.

Include these sections:
1. **Total Budget Summary** — Overview with total and per-guest cost
2. **Category Breakdown** — Detailed line items for: Venue, Catering & Bar, Photography/Video, Flowers & Decor, Music/DJ, Wedding Attire, Cake & Desserts, Stationery, Transportation, Gifts & Favors, Miscellaneous
3. **Priority Allocation** — Must-haves vs nice-to-haves based on their preferences
4. **Cost-Saving Tips** — Specific suggestions based on their choices
5. **Payment Timeline** — When deposits and payments are typically due

Format using markdown with actual estimated dollar amounts where possible.""",

    # ── Product Launch ───────────────────────────────────────
    "launch_plan": """You are a product launch strategist. Based on the consultation Q&A below, generate a comprehensive launch plan.

Include these sections:
1. **Product Positioning** — Value proposition, key differentiators, messaging framework
2. **Target Audience** — Primary personas, segments, pain points addressed
3. **Go-to-Market Strategy** — Channels, tactics, partnerships, pricing strategy
4. **Launch Timeline** — Pre-launch (8-12 weeks), launch week, post-launch phases
5. **Content & Marketing Plan** — Content calendar, PR strategy, social media plan
6. **Success Metrics & KPIs** — Targets for first 30/60/90 days
7. **Risk Mitigation** — Potential issues and contingency plans

Format using markdown. Be actionable and specific.""",

    "launch_checklist": """You are a product launch coordinator. Based on the consultation Q&A below, generate a detailed launch checklist.

Include these sections:
1. **Pre-Launch Checklist** — Everything to complete before launch day
2. **Launch Day Checklist** — Hour-by-hour activities for launch day
3. **Post-Launch Checklist** — Follow-up actions for the first week
4. **Marketing Assets Needed** — List of all content and materials to prepare
5. **Team Responsibilities** — Who does what and when

Format as actionable checklists with checkboxes (- [ ]).""",

    # ── Event Planning ───────────────────────────────────────
    "event_plan": """You are a professional event planner. Based on the consultation Q&A below, generate a comprehensive event plan.

Include these sections:
1. **Event Overview** — Concept, goals, target audience, expected outcomes
2. **Budget Breakdown** — Estimated allocation per category
3. **Venue & Logistics** — Layout, A/V requirements, accessibility, parking
4. **Program Schedule** — Detailed agenda with timing
5. **Vendor & Service Providers** — Caterers, A/V, decor, entertainment, staffing
6. **Promotion Plan** — How to attract and register attendees
7. **Day-of Run Sheet** — Minute-by-minute operations plan
8. **Post-Event Follow-up** — Feedback collection, thank-yous, reporting

Format using markdown. Be specific based on their answers.""",

    "event_budget": """You are an event budget specialist. Based on the consultation Q&A below, generate a detailed event budget.

Include these sections:
1. **Total Budget Summary** — Overview with per-attendee cost
2. **Category Breakdown** — Venue, Catering, A/V & Tech, Decor, Entertainment, Marketing, Staffing, Insurance, Miscellaneous
3. **Revenue Projections** — If applicable (ticket sales, sponsorships)
4. **Cost-Saving Opportunities** — Based on their preferences
5. **Contingency Budget** — 10-15% reserve recommendations

Format using markdown with estimated amounts.""",

    # ── Business Strategy ────────────────────────────────────
    "strategy_plan": """You are a business strategy consultant. Based on the consultation Q&A below, generate a comprehensive strategy document.

Include these sections:
1. **Executive Summary** — Business vision and strategic direction
2. **Market Analysis** — Market size, trends, opportunities, threats (SWOT)
3. **Competitive Positioning** — Key competitors, differentiation strategy
4. **Business Model** — Revenue streams, cost structure, value chain
5. **Growth Strategy** — Customer acquisition, expansion plans, partnerships
6. **Execution Roadmap** — Quarterly milestones for the next 12 months
7. **Resource Requirements** — Team, technology, funding needs
8. **Risk Assessment** — Key risks and mitigation strategies

Format using markdown. Ground recommendations in the consultation answers.""",

    "action_plan": """You are a business execution coach. Based on the consultation Q&A below, generate a prioritized action plan.

Include these sections:
1. **Immediate Actions (This Week)** — Quick wins and urgent items
2. **Short-term Goals (30 Days)** — Key milestones to hit
3. **Medium-term Goals (90 Days)** — Growth targets and infrastructure
4. **Long-term Vision (12 Months)** — Strategic objectives
5. **Key Decisions Needed** — Open questions that need resolution
6. **Resource Allocation** — Where to focus time and money first

Format as actionable items with clear owners and deadlines where possible.""",

    # ── Q&A Helper / Generic ─────────────────────────────────
    "analysis": """You are an expert analyst. Based on the consultation Q&A below, generate a comprehensive analysis document.

Include these sections:
1. **Problem Statement** — Clear definition of the question/problem
2. **Context & Background** — Relevant factors and constraints
3. **Options Analysis** — Pros, cons, and trade-offs of each option discussed
4. **Recommendation** — Best path forward with reasoning
5. **Action Items** — Concrete next steps
6. **Risks & Considerations** — What to watch out for

Format using markdown. Be thorough and reference specific answers.""",

    "summary_report": """You are a professional consultant. Based on the consultation Q&A below, generate a summary report.

Include these sections:
1. **Overview** — What was discussed and why
2. **Key Findings** — Main insights from the consultation
3. **Decisions Made** — Clear list of all decisions and choices
4. **Recommendations** — Suggested next steps
5. **Open Items** — Questions that still need answers

Format using markdown. Keep it concise and actionable.""",

    # ── Security Review ──────────────────────────────────────
    "security_report": """You are a cybersecurity consultant. Based on the consultation Q&A below, generate a security assessment report.

Include these sections:
1. **Executive Summary** — Overall security posture assessment
2. **System Overview** — Architecture and data flow from security perspective
3. **Threat Model** — Identified threats, attack vectors, and risk levels
4. **Vulnerability Assessment** — Current gaps and weaknesses
5. **Security Recommendations** — Prioritized remediation steps (Critical/High/Medium/Low)
6. **Compliance Status** — Regulatory requirements and gaps
7. **Implementation Roadmap** — Phased security improvement plan

Format using markdown. Prioritize by risk level.""",
}

# Map each mode to its available doc types (label, doc_type_key, icon_name)
MODE_DOC_TYPES: dict[str, list[dict]] = {
    "software_architecture": [
        {"label": "System Architecture", "doc_type": "architecture", "icon": "grid"},
        {"label": "Project Documentation", "doc_type": "documentation", "icon": "file-text"},
    ],
    "api_design": [
        {"label": "API Architecture", "doc_type": "architecture", "icon": "grid"},
        {"label": "API Documentation", "doc_type": "documentation", "icon": "file-text"},
    ],
    "data_pipeline": [
        {"label": "Pipeline Architecture", "doc_type": "architecture", "icon": "grid"},
        {"label": "Pipeline Documentation", "doc_type": "documentation", "icon": "file-text"},
    ],
    "cloud_migration": [
        {"label": "Migration Architecture", "doc_type": "architecture", "icon": "grid"},
        {"label": "Migration Plan", "doc_type": "documentation", "icon": "file-text"},
    ],
    "security_review": [
        {"label": "Security Report", "doc_type": "security_report", "icon": "shield"},
        {"label": "Detailed Documentation", "doc_type": "documentation", "icon": "file-text"},
    ],
    "wedding_planner": [
        {"label": "Wedding Plan", "doc_type": "wedding_plan", "icon": "heart"},
        {"label": "Budget Breakdown", "doc_type": "wedding_budget", "icon": "dollar"},
    ],
    "product_launch": [
        {"label": "Launch Plan", "doc_type": "launch_plan", "icon": "rocket"},
        {"label": "Launch Checklist", "doc_type": "launch_checklist", "icon": "check-list"},
    ],
    "event_planning": [
        {"label": "Event Plan", "doc_type": "event_plan", "icon": "calendar"},
        {"label": "Event Budget", "doc_type": "event_budget", "icon": "dollar"},
    ],
    "business_strategy": [
        {"label": "Strategy Document", "doc_type": "strategy_plan", "icon": "trending-up"},
        {"label": "Action Plan", "doc_type": "action_plan", "icon": "check-list"},
    ],
    "qa_helper": [
        {"label": "Analysis Report", "doc_type": "analysis", "icon": "search"},
        {"label": "Summary Report", "doc_type": "summary_report", "icon": "file-text"},
    ],
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
