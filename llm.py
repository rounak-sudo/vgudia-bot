"""One place that calls Claude and returns schema-checked JSON."""
from __future__ import annotations

import json
import os

import anthropic

MODEL = os.getenv("CLAUDE_MODEL") or "claude-opus-5-5"


class LLMError(RuntimeError):
    pass


def ask_json(system: str, content, schema: dict, effort: str = "medium") -> dict:
    """Send one request and return the JSON object Claude produced (matching `schema`)."""
    client = anthropic.Anthropic()
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        # If a request is declined by the model's safety checks, the API retries it on a
        # suitable fallback model instead of failing.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        system=system,
        messages=[{"role": "user", "content": content}],
    )
    if response.stop_reason == "refusal":
        raise LLMError(f"Claude declined the request: {response.stop_details}")
    if response.stop_reason == "max_tokens":
        raise LLMError("Claude's answer was cut off (max_tokens)")
    text = next((b.text for b in response.content if b.type == "text"), None)
    if not text:
        raise LLMError("Claude returned no text")
    return json.loads(text)
