"""Publish a finished draft to Instagram (always) and the LinkedIn Company Page (top stories only).

Each platform is recorded in entry["done"] as soon as it succeeds, so a retry never posts twice.
"""
from __future__ import annotations

import os

from . import instagram, linkedin, state, telegram_bot

LINKEDIN_MAX_PER_DAY = int(os.getenv("LINKEDIN_MAX_PER_DAY") or "4")
LINKEDIN_MIN_IMPORTANCE = int(os.getenv("LINKEDIN_MIN_IMPORTANCE") or "4")


def _read(draft_id: str, name: str) -> str:
    with open(os.path.join(state.DRAFTS_DIR, draft_id, name), encoding="utf-8") as f:
        return f.read()


def _linkedin_today(st: dict) -> int:
    today = state.now_ist().date().isoformat()
    return sum(1 for d in st.setdefault("linkedin_log", []) if d.startswith(today))


def wants_linkedin(st: dict, entry: dict) -> bool:
    return (linkedin.enabled()
            and entry.get("importance", 0) >= LINKEDIN_MIN_IMPORTANCE
            and _linkedin_today(st) < LINKEDIN_MAX_PER_DAY)


def publish_entry(st: dict, draft_id: str, entry: dict) -> tuple[bool, list[str]]:
    """Returns (finished, report lines). finished=False means something failed and can be retried."""
    done = entry.setdefault("done", {})
    report: list[str] = []
    ok = True

    if "instagram" not in done:
        try:
            urls = [state.public_url(p) for p in entry["images"]]
            done["instagram"] = instagram.publish(urls, _read(draft_id, "caption.txt"))
            state.save(st)
        except instagram.InstagramError as e:
            ok = False
            report.append(f"❌ Instagram: {e}")
    if "instagram" in done:
        report.append(f"📸 Instagram: {done['instagram']}")

    if "linkedin" not in done and entry.get("linkedin_decided") is None:
        entry["linkedin_decided"] = wants_linkedin(st, entry)  # decide once, at first attempt
    if entry.get("linkedin_decided") and "linkedin" not in done:
        try:
            paths = [os.path.join(state.ROOT, p) for p in entry["images"]]
            done["linkedin"] = linkedin.publish(paths, _read(draft_id, "linkedin.txt"))
            st.setdefault("linkedin_log", []).append(state.now_ist().isoformat())
            state.save(st)
        except linkedin.LinkedInError as e:
            ok = False
            report.append(f"❌ LinkedIn: {e}")
    if "linkedin" in done:
        report.append(f"💼 LinkedIn: {done['linkedin']}")

    if ok:
        st["posted"].append({"id": draft_id, "headline": entry["headline"],
                             "posted": state.now_ist().isoformat(), "links": done})
        st["pending"].pop(draft_id, None)
    return ok, report


def notify(text: str) -> None:
    """Telegram message if Telegram is configured; otherwise just print it."""
    print(text)
    if os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
        try:
            telegram_bot.send_text(text)
        except Exception as e:  # a failed notification must never stop posting
            print(f"(Telegram notification failed: {e})")
