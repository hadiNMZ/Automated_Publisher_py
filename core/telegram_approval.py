"""
Interactive Telegram approval gate. Sends a file with Approve/Deny
inline buttons, then BLOCKS (polls Telegram) until you tap one — this
is the real gate your original n8n workflow only approximated with a
plain notify message.

Uses long-polling (getUpdates), which is fine for a single personal
bot used by one pipeline at a time. If you later run multiple plugins
concurrently against the same bot, this would need a shared offset
file to avoid one plugin consuming another's update — not needed for
sequential daily runs.
"""
import json
import time
import requests
from pathlib import Path
from config_base import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, APPROVAL_TIMEOUT_SECONDS

API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

_KEYBOARD = {
    "inline_keyboard": [[
        {"text": "✅ Approve", "callback_data": "approve"},
        {"text": "❌ Deny", "callback_data": "deny"},
    ]]
}


def _send_with_buttons(method: str, file_field: str, file_path: Path, caption: str) -> int:
    with open(file_path, "rb") as f:
        resp = requests.post(
            f"{API_BASE}/{method}",
            data={
                "chat_id": TELEGRAM_CHAT_ID,
                "caption": caption,
                "reply_markup": json.dumps(_KEYBOARD),
            },
            files={file_field: f},
            timeout=60,
        )
    resp.raise_for_status()
    return resp.json()["result"]["message_id"]


def _wait_for_answer(message_id: int) -> bool:
    """Blocks until someone taps Approve/Deny on this specific message,
    or raises TimeoutError after APPROVAL_TIMEOUT_SECONDS."""
    offset = None
    elapsed = 0
    poll_interval = 5

    while elapsed < APPROVAL_TIMEOUT_SECONDS:
        params = {"timeout": poll_interval}
        if offset is not None:
            params["offset"] = offset

        resp = requests.get(f"{API_BASE}/getUpdates", params=params, timeout=poll_interval + 10)
        resp.raise_for_status()

        for update in resp.json()["result"]:
            offset = update["update_id"] + 1
            cq = update.get("callback_query")
            if cq and cq["message"]["message_id"] == message_id:
                requests.post(f"{API_BASE}/answerCallbackQuery",
                               data={"callback_query_id": cq["id"]})
                return cq["data"] == "approve"

        elapsed += poll_interval

    raise TimeoutError(
        f"No approve/deny response within {APPROVAL_TIMEOUT_SECONDS} seconds."
    )


def send_audio_for_approval(audio_path: Path, caption: str) -> bool:
    message_id = _send_with_buttons("sendAudio", "audio", audio_path, caption)
    return _wait_for_answer(message_id)


def send_video_for_approval(video_path: Path, caption: str) -> bool:
    message_id = _send_with_buttons("sendVideo", "video", video_path, caption)
    return _wait_for_answer(message_id)


def send_message(text: str) -> None:
    requests.post(f"{API_BASE}/sendMessage",
                  data={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=30)
