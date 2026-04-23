# anony/helpers/styled_send.py

import json
import os
import aiohttp

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

# This error is harmless — happens when timer tries to update
# but the markup hasn't changed yet. Suppress it silently.
_IGNORE_ERRORS = {"message is not modified"}


def _markup(markup) -> str:
    rows = []
    for row in markup.inline_keyboard:
        btn_row = []
        for btn in row:
            d = {"text": btn.text}
            if getattr(btn, "style", None):
                d["style"] = btn.style
            if getattr(btn, "callback_data", None) is not None:
                d["callback_data"] = btn.callback_data
            elif getattr(btn, "url", None):
                d["url"] = btn.url
            elif getattr(btn, "switch_inline_query", None) is not None:
                d["switch_inline_query"] = btn.switch_inline_query
            elif getattr(btn, "switch_inline_query_current_chat", None) is not None:
                d["switch_inline_query_current_chat"] = btn.switch_inline_query_current_chat
            btn_row.append(d)
        rows.append(btn_row)
    return json.dumps({"inline_keyboard": rows})


def _log_error(fn_name: str, result: dict) -> None:
    desc = result.get("description", "")
    # Suppress harmless "not modified" errors from timer updates
    if any(e in desc for e in _IGNORE_ERRORS):
        return
    print(f"[styled_send] {fn_name} error: {result}")


async def send_styled_video(
    chat_id: int,
    video: str,
    caption: str,
    reply_markup=None,
    parse_mode: str = "html",
    reply_to_message_id: int = None,
) -> dict:
    data = {
        "chat_id": chat_id,
        "video": video,
        "caption": caption,
        "parse_mode": parse_mode,
    }
    if reply_markup:
        data["reply_markup"] = _markup(reply_markup)
    if reply_to_message_id:
        data["reply_to_message_id"] = reply_to_message_id
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE}/sendVideo", data=data) as resp:
            result = await resp.json()
            if not result.get("ok"):
                _log_error("sendVideo", result)
            return result


async def send_styled(
    chat_id: int,
    text: str,
    reply_markup=None,
    parse_mode: str = "html",
    reply_to_message_id: int = None,
) -> dict:
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    if reply_markup:
        data["reply_markup"] = _markup(reply_markup)
    if reply_to_message_id:
        data["reply_to_message_id"] = reply_to_message_id
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE}/sendMessage", data=data) as resp:
            result = await resp.json()
            if not result.get("ok"):
                _log_error("sendMessage", result)
            return result


async def edit_styled(
    chat_id: int,
    message_id: int,
    reply_markup=None,
) -> dict:
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
    }
    if reply_markup:
        data["reply_markup"] = _markup(reply_markup)
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE}/editMessageReplyMarkup", data=data) as resp:
            result = await resp.json()
            if not result.get("ok"):
                _log_error("editMarkup", result)
            return result


async def edit_caption_styled(
    chat_id: int,
    message_id: int,
    caption: str,
    reply_markup=None,
    parse_mode: str = "html",
) -> dict:
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "caption": caption,
        "parse_mode": parse_mode,
    }
    if reply_markup:
        data["reply_markup"] = _markup(reply_markup)
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE}/editMessageCaption", data=data) as resp:
            result = await resp.json()
            if not result.get("ok"):
                _log_error("editCaption", result)
            return result


async def edit_text_styled(
    chat_id: int,
    message_id: int,
    text: str,
    reply_markup=None,
    parse_mode: str = "html",
) -> dict:
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    if reply_markup:
        data["reply_markup"] = _markup(reply_markup)
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE}/editMessageText", data=data) as resp:
            result = await resp.json()
            if not result.get("ok"):
                _log_error("editText", result)
            return result