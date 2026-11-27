"""Automatic fact check that replaces a human approval: every number / name in the post
must be backed by the source story. (The poster text is typed from the same checked
content, so it cannot be misspelled or invented.)
"""
from __future__ import annotations

import json

from llm import ask_json
from news import Story

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


def check_facts(plan: dict, story: Story) -> tuple[bool, list[str]]:
    post = {k: plan.get(k) for k in ("headline", "banner", "data_title", "data_items", "cards",
                                     "slides", "caption", "linkedin_text")}
    content = (f"SOURCE STORY ({story.source}):\nHEADLINE: {story.headline}\nTEXT: {story.body}\n\n"
               f"POST TO CHECK (JSON):\n{json.dumps(post, ensure_ascii=False, indent=1)}")
    result = ask_json(FACT_SYSTEM, content, RESULT_SCHEMA)
    return bool(result["ok"]), result["problems"]
