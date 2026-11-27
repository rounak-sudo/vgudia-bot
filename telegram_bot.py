"""Send drafts to the owner's Telegram chat and read their button taps."""
from __future__ import annotations

import json
import os

import requests


def _api(method: str) -> str:
    return f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/{method}"


def _chat_id() -> str:
    return os.environ["TELEGRAM_CHAT_ID"]


def _post(method: str, files=None, **data) -> dict:
    for k, v in list(data.items()):
        if isinstance(v, (dict, list)):
            data[k] = json.dumps(v)
    r = requests.post(_api(method), data=data, files=files, timeout=60)
    body = r.json()
    if not body.get("ok"):
        # Never include the URL in errors: it contains the bot token.
        raise RuntimeError(f"Telegram {method} failed: {body.get('description')}")
    return body["result"]


def buttons(draft_id: str) -> dict:
    return {"inline_keyboard": [
        [{"text": "✅ Approve & post", "callback_data": f"a:{draft_id}"},
         {"text": "❌ Reject", "callback_data": f"r:{draft_id}"}],
        [{"text": "🔁 New image", "callback_data": f"g:{draft_id}"}],
    ]}


def send_draft(draft_id: str, image_paths: list[str], title: str, caption: str) -> int:
    """Send poster (or carousel album) + caption with approval buttons. Returns the buttons message id."""
    label = f"{title}"[:1024]
    if len(image_paths) == 1:
        with open(image_paths[0], "rb") as f:
            _post("sendPhoto", files={"photo": f}, chat_id=_chat_id(), caption=label)
    else:
        handles = {f"p{i}": open(p, "rb") for i, p in enumerate(image_paths[:10])}
        try:
            media = [{"type": "photo", "media": f"attach://{k}"} for k in handles]
            media[0]["caption"] = label
            _post("sendMediaGroup", files=handles, chat_id=_chat_id(), media=media)
        finally:
            for h in handles.values():
                h.close()
    msg = _post("sendMessage", chat_id=_chat_id(), text=caption[:4000],
                reply_markup=buttons(draft_id))
    return msg["message_id"]


def send_text(text: str) -> None:
    _post("sendMessage", chat_id=_chat_id(), text=text[:4000], disable_web_page_preview="true")


def get_updates(offset: int) -> list[dict]:
    return _post("getUpdates", offset=offset, timeout=0,
                 allowed_updates=["callback_query"])


def answer_callback(callback_id: str, text: str) -> None:
    try:
        _post("answerCallbackQuery", callback_query_id=callback_id, text=text[:200])
    except RuntimeError:
        pass  # callbacks older than a few minutes can no longer be answered; harmless


def remove_buttons(message_id: int) -> None:
    try:
        _post("editMessageReplyMarkup", chat_id=_chat_id(), message_id=message_id,
              reply_markup={"inline_keyboard": []})
    except RuntimeError:
        pass


def is_owner(callback: dict) -> bool:
    """Only the owner's own chat may approve. Anyone can find a bot, so check every tap."""
    owner = str(_chat_id())
    chat = str(callback.get("message", {}).get("chat", {}).get("id", ""))
    sender = str(callback.get("from", {}).get("id", ""))
    return chat == owner and sender == owner
