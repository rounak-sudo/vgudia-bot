"""Automatic quality checks that replace a human approval:
1. check_facts  - every number / name in the post is backed by the source story.
2. check_image  - the generated poster shows exactly the intended text, nothing invented, no logos.
"""
from __future__ import annotations

import base64
import json

from .llm import ask_json
from .news import Story

RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "ok": {"type": "boolean"},
        "problems": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["ok", "problems"],
    "additionalProperties": False,
}

FACT_SYSTEM = """You are the fact-checker of vGudia, a Bengali financial-news page. A post goes live automatically if you pass it, so be strict about facts and relaxed about style.

Compare the post (Bengali poster texts, carousel slides, Instagram caption, LinkedIn text) with the English source story.
FAIL (ok=false) if any of these is true:
- A number, percentage, price, date, index level or amount in the post is not in the source, or differs from it (Bengali digits are fine: ৩.৫ = 3.5).
- A company, person, country or institution is named in the post but not in the source, or a fact is attributed to the wrong one.
- The post states something the source does not say, or reverses its meaning (rise vs fall, buy vs sell).
- The post gives investment advice (telling readers to buy or sell).
PASS (ok=true) for wording, tone, translation choices, hashtags, the standard disclaimer and source line, and general context that adds no new facts.
List each concrete problem briefly in English."""

IMAGE_SYSTEM = """You check AI-generated Bengali news posters for vGudia before they are published automatically.
You get the poster image and the list of texts that must appear on it.
FAIL (ok=false) if:
- Any required Bengali text is misspelled, has wrong or broken letters/conjuncts, missing or extra words, or is unreadable.
- Any required number differs from the list.
- The image contains extra numbers, prices, percentages, index levels or tickers that are not in the list (for example on a screen or board in the background).
- The image shows a company logo, emblem or trademark.
- Text is cut off at the edges or covered.
Ignore small differences in punctuation spacing and line breaks. List each concrete problem briefly in English."""


def check_facts(plan: dict, story: Story) -> tuple[bool, list[str]]:
    post = {k: plan.get(k) for k in ("headline", "banner", "data_title", "data_items", "cards",
                                     "slides", "caption", "linkedin_text")}
    content = (f"SOURCE STORY ({story.source}):\nHEADLINE: {story.headline}\nTEXT: {story.body}\n\n"
               f"POST TO CHECK (JSON):\n{json.dumps(post, ensure_ascii=False, indent=1)}")
    result = ask_json(FACT_SYSTEM, content, RESULT_SCHEMA, effort="medium")
    return bool(result["ok"]), result["problems"]


def check_image(image_path: str, required_texts: list[str]) -> tuple[bool, list[str]]:
    with open(image_path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    listing = "\n".join(f"- {t}" for t in required_texts)
    content = [
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}},
        {"type": "text", "text": f"Texts that must appear exactly on this poster:\n{listing}\n\nCheck the poster."},
    ]
    result = ask_json(IMAGE_SYSTEM, content, RESULT_SCHEMA, effort="medium")
    return bool(result["ok"]), result["problems"]
