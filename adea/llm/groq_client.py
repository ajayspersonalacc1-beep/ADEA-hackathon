"""Groq API client wrapper for JSON generation."""

from __future__ import annotations

from contextvars import ContextVar
import json
import os
from json import JSONDecodeError
from typing import TYPE_CHECKING, Any

from dotenv import load_dotenv
from sqlglot import exp, parse, parse_one
from sqlglot.errors import ParseError

try:
    import groq
    from groq import Groq
except ImportError:
    groq = None
    Groq = None

if TYPE_CHECKING:
    from groq import Groq as GroqClient
else:
    GroqClient = Any


DEFAULT_MODEL = "llama-3.3-70b-versatile"
MAX_PARSE_RETRIES = 3
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_CLIENT_RETRIES = 2
MAX_LLM_CALLS_PER_RUN = 10
LLM_BUDGET_MESSAGE = "LLM call limit reached, switching to deterministic fallback."
LLM_CONNECTION_MESSAGE = (
    "Groq connection unavailable for this workflow, switching to deterministic fallback."
)
_LLM_CALL_COUNTER: ContextVar[int] = ContextVar("adea_llm_call_counter", default=0)
_LLM_CONNECTION_DISABLED: ContextVar[bool] = ContextVar(
    "adea_llm_connection_disabled",
    default=False,
)
_ALLOWED_SQL_EXPRESSIONS = (exp.Select, exp.Insert, exp.Create)

load_dotenv()


def _clean_response(text: str) -> str:
    """Remove markdown code fences if the model returns them."""
    text = text.strip()

    if text.startswith("```"):
        text = text.split("```")[1]

    return text.strip()


def _get_api_key() -> str | None:
    """Return the configured Groq API key from the environment."""

    api_key = os.getenv("GROQ_API_KEY")
    if isinstance(api_key, str) and api_key.strip():
        return api_key.strip()

    return None


def _get_timeout_seconds() -> float:
    """Return the configured Groq request timeout."""

    raw_timeout = os.getenv("GROQ_TIMEOUT_SECONDS")
    if not raw_timeout:
        return DEFAULT_TIMEOUT_SECONDS

    try:
        timeout_seconds = float(raw_timeout)
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS

    return timeout_seconds if timeout_seconds > 0 else DEFAULT_TIMEOUT_SECONDS


def _get_client_retries() -> int:
    """Return the configured SDK retry count."""

    raw_retries = os.getenv("GROQ_CLIENT_RETRIES")
    if not raw_retries:
        return DEFAULT_CLIENT_RETRIES

    try:
        retry_count = int(raw_retries)
    except ValueError:
        return DEFAULT_CLIENT_RETRIES

    return retry_count if retry_count >= 0 else DEFAULT_CLIENT_RETRIES


def _build_client() -> GroqClient | None:
    """Create a Groq client from the current environment."""

    api_key = _get_api_key()
    if Groq is None or api_key is None:
        return None

    return Groq(
        api_key=api_key,
        timeout=_get_timeout_seconds(),
        max_retries=_get_client_retries(),
    )


def reset_llm_budget() -> None:
    """Reset the per-workflow LLM call counter."""

    _LLM_CALL_COUNTER.set(0)
    _LLM_CONNECTION_DISABLED.set(False)


def validate_sql_statement(query: str) -> tuple[bool, str]:
    """Validate that the SQL statement is a single allowed AST node."""

    if not isinstance(query, str) or not query.strip():
        return False, "SQL statement is empty."

    try:
        statements = parse(query)
    except ParseError as exc:
        return False, f"SQL parsing failed: {exc}"

    if len(statements) != 1:
        return False, "Only single-statement SQL is allowed."

    parsed = statements[0]
    if parsed is None:
        return False, "SQL parsing returned no statements."

    if not isinstance(parsed, _ALLOWED_SQL_EXPRESSIONS):
        return False, (
            "Only CREATE, INSERT, SELECT, and WITH-backed SQL statements are allowed."
        )

    if isinstance(parsed, exp.Create):
        kind = str(parsed.args.get("kind", "")).upper()
        if kind not in {"", "TABLE"}:
            return False, "Only CREATE TABLE statements are allowed."

    return True, ""


def generate_json(prompt: str) -> dict[str, Any]:
    """Generate JSON from Groq chat completions with safe parsing and retries."""

    if Groq is None or groq is None:
        return {"success": False, "error": "groq package is not installed."}

    if _LLM_CONNECTION_DISABLED.get():
        return {"success": False, "error": LLM_CONNECTION_MESSAGE}

    current_count = _LLM_CALL_COUNTER.get()
    if current_count >= MAX_LLM_CALLS_PER_RUN:
        return {"success": False, "error": LLM_BUDGET_MESSAGE}

    _LLM_CALL_COUNTER.set(current_count + 1)

    client = _build_client()
    if client is None:
        return {"success": False, "error": "GROQ_API_KEY is not set."}

    last_error: str | None = None

    for attempt in range(1, MAX_PARSE_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=DEFAULT_MODEL,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You must return ONLY valid JSON. "
                            "No markdown, no explanations."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
            )

        except groq.APIConnectionError as exc:
            _LLM_CONNECTION_DISABLED.set(True)
            return {
                "success": False,
                "error": (
                    f"{LLM_CONNECTION_MESSAGE} Details: {exc}"
                ),
            }

        except groq.APIError as exc:
            return {"success": False, "error": f"Groq API error: {exc}"}

        except Exception as exc:
            return {"success": False, "error": f"Unexpected Groq error: {exc}"}

        content = response.choices[0].message.content if response.choices else None

        if not isinstance(content, str) or not content.strip():
            last_error = "Groq returned empty response."
            continue

        content = _clean_response(content)

        try:
            parsed = json.loads(content)
        except JSONDecodeError as exc:
            last_error = f"JSON parse failed (attempt {attempt}): {exc}"
            continue

        if isinstance(parsed, dict):
            parsed["success"] = True
            return parsed

        return {"success": True, "result": parsed}

    return {"success": False, "error": last_error or "Unknown JSON parsing error."}
