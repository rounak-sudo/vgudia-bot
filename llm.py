"""One place that calls the AI writer and returns schema-checked JSON.

Uses Google's Gemini API, which has a free tier (get a key at aistudio.google.com).
"""
from __future__ import annotations

import json
import os
import time

from google import genai
from google.genai import errors, types

MODEL = os.getenv("GEMINI_MODEL") or "gemini-2.5-flash"


class LLMError(RuntimeError):
    pass


def ask_json(system: str, content: str, schema: dict, effort: str = "medium") -> dict:
    """Send one request and return the JSON object the model produced (matching `schema`).

    `effort` is kept for compatibility with the callers; Gemini decides its own thinking.
    """
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    config = types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json",
        response_json_schema=schema,
        temperature=0.4,
    )
    last_error = None
    for attempt in range(4):
        try:
            response = client.models.generate_content(model=MODEL, contents=content, config=config)
            text = response.text
            if not text:
                raise LLMError("Gemini returned no text (possibly blocked by its safety filter)")
            return json.loads(text)
        except errors.APIError as e:
            last_error = e
            # 429 = free-tier rate limit, 5xx = temporary problem: wait and try again.
            if getattr(e, "code", None) in (429, 500, 502, 503, 504):
                time.sleep(20 * (attempt + 1))
                continue
            raise LLMError(f"Gemini error {getattr(e, 'code', '')}: {e}") from e
        except json.JSONDecodeError as e:
            last_error = e
            continue
    raise LLMError(f"Gemini failed after retries: {last_error}")
