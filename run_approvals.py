"""Every ~15 minutes: handle taps on FLAGGED drafts (ones that failed the automatic poster check),
expire old drafts and clean up. Normal drafts never come here: they are posted automatically.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import sys
import traceback

import state, telegram_bot
from poster import generate_image
from publisher import publish_entry

PENDING_HOURS = int(os.getenv("PENDING_HOURS") or "6")   # unhandled drafts expire (news goes stale)
KEEP_DRAFT_DAYS = 3                                       # old draft folders are deleted


def new_images(draft_id: str, entry: dict) -> None:
    folder = os.path.join(state.DRAFTS_DIR, draft_id)
    with open(os.path.join(folder, "prompts.json"), encoding="utf-8") as f:
        prompts = json.load(f)
    with open(os.path.join(folder, "caption.txt"), encoding="utf-8") as f:
        caption = f.read()
    entry["version"] += 1
    images = []
    for i, prompt in enumerate(prompts):
        # New file names each time so Instagram never gets a cached older image.
        rel = f"drafts/{draft_id}/v{entry['version']}-{i + 1}.jpg"
        generate_image(prompt, os.path.join(state.ROOT, rel))
        images.append(rel)
    entry["images"] = images
    entry["message_id"] = telegram_bot.send_draft(
        draft_id, [os.path.join(state.ROOT, p) for p in images],
        f"🔁 New images (v{entry['version']}): {entry['title']}", caption)


def handle(st: dict, cb: dict) -> None:
    if not telegram_bot.is_owner(cb):
        telegram_bot.answer_callback(cb["id"], "Not allowed.")
        return
    action, _, draft_id = cb.get("data", "").partition(":")
    entry = st["pending"].get(draft_id)
    msg_id = cb.get("message", {}).get("message_id")
    if not entry or entry.get("status") not in ("review", "approved"):
        telegram_bot.answer_callback(cb["id"], "This draft was already handled or expired.")
        if msg_id:
            telegram_bot.remove_buttons(msg_id)
        return

    if action == "a":
        telegram_bot.answer_callback(cb["id"], "Posting…")
        entry["status"] = "approved"
        finished, report = publish_entry(st, draft_id, entry)
        if finished:
            if msg_id:
                telegram_bot.remove_buttons(msg_id)
            telegram_bot.send_text(f"✅ Posted: {entry['title']}\n" + "\n".join(report))
        else:
            telegram_bot.send_text("Not fully posted:\n" + "\n".join(report) + "\nTap Approve again to retry.")
    elif action == "r":
        del st["pending"][draft_id]
        if msg_id:
            telegram_bot.remove_buttons(msg_id)
        telegram_bot.answer_callback(cb["id"], "Rejected.")
    elif action == "g":
        telegram_bot.answer_callback(cb["id"], "Making new images…")
        if msg_id:
            telegram_bot.remove_buttons(msg_id)
        new_images(draft_id, entry)


def expire_and_clean(st: dict) -> None:
    now = state.now_ist()
    expired = [d for d, e in st["pending"].items()
               if e.get("status") != "ready"
               and now - dt.datetime.fromisoformat(e["created"]) > dt.timedelta(hours=PENDING_HOURS)]
    for d in expired:
        if st["pending"][d].get("message_id"):
            telegram_bot.remove_buttons(st["pending"][d]["message_id"])
        del st["pending"][d]
    if expired:
        print("Expired:", expired)

    if os.path.isdir(state.DRAFTS_DIR):
        cutoff = (now - dt.timedelta(days=KEEP_DRAFT_DAYS)).strftime("%Y%m%d")
        for name in os.listdir(state.DRAFTS_DIR):
            if name not in st["pending"] and name[:8] < cutoff:
                shutil.rmtree(os.path.join(state.DRAFTS_DIR, name), ignore_errors=True)


def main() -> None:
    st = state.load()
    if os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
        updates = telegram_bot.get_updates(st["tg_offset"])
        if updates:
            # Acknowledge every tap with Telegram BEFORE acting on it. If this run then crashes,
            # a tap is lost (just tap again) but a post can never be published twice from one tap.
            st["tg_offset"] = updates[-1]["update_id"] + 1
            telegram_bot.get_updates(st["tg_offset"])
            state.save(st)
        for upd in updates:
            cb = upd.get("callback_query")
            if cb:
                try:
                    handle(st, cb)
                except Exception as exc:
                    traceback.print_exc()
                    telegram_bot.send_text(f"⚠️ Could not handle that tap: {type(exc).__name__}: {exc}"[:600])
            state.save(st)
        print(f"Handled {len(updates)} Telegram updates.")
    expire_and_clean(st)
    state.save(st)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
