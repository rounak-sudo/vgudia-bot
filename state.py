"""Tiny JSON state kept in the repo (the GitHub workflow commits it after each run)."""
from __future__ import annotations

import datetime as dt
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
STATE_DIR = os.path.join(ROOT, "state")
DRAFTS_DIR = os.path.join(ROOT, "drafts")
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))

DEFAULTS = {"seen": [], "pending": {}, "posted": [], "tg_offset": 0}


def now_ist() -> dt.datetime:
    return dt.datetime.now(IST)


def load() -> dict:
    path = os.path.join(STATE_DIR, "state.json")
    if not os.path.exists(path):
        return json.loads(json.dumps(DEFAULTS))
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    for k, v in DEFAULTS.items():
        data.setdefault(k, v)
    return data


def save(data: dict) -> None:
    os.makedirs(STATE_DIR, exist_ok=True)
    data["seen"] = data["seen"][-1500:]
    data["posted"] = data["posted"][-200:]
    path = os.path.join(STATE_DIR, "state.json")
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(path + ".tmp", path)


def public_url(rel_path: str) -> str:
    """Public URL Instagram downloads the poster from (the repo must be public)."""
    base = os.getenv("PUBLIC_BASE_URL")
    if not base:
        repo = os.environ["GITHUB_REPOSITORY"]
        branch = os.getenv("GITHUB_REF_NAME", "main")
        base = f"https://raw.githubusercontent.com/{repo}/{branch}"
    return f"{base.rstrip('/')}/{rel_path.replace(os.sep, '/')}"
