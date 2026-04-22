# anony/helper/styled_send.py
#
# Sends messages/videos with coloured buttons via HTTP Bot API.
# kurigram (MTProto) ignores style= — HTTP Bot API respects it.
# Uses your existing BOT_TOKEN from .env — no new variable needed.

import json
import os
import aiohttp

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"


def _markup(markup) -> str:
    """Convert kurigram InlineKeyboardMarkup → HTTP Bot API JSON string."""
    rows = []
    for row in markup.inline_keyboard:
        btn_row = []
        for btn in row:
            d = {"text": btn.text}
            # style= colour stored by inline.py / buttons.py as plain attribute
            if getattr(btn, "style", None):
                d["style"] = btn.style
            # action
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


async def send_styled_video(
    chat_id: int,
    video: str,
    caption: str,
    reply_markup=None,
    parse_mode: str = "html",
    reply_to_message_id: int = None,
) -> dict:
    """Send a video with coloured inline buttons — replaces message.reply_video()."""
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
                print(f"[styled_send] sendVideo error: {result}")
            return result


async def send_styled(
    chat_id: int,
    text: str,
    reply_markup=None,
    parse_mode: str = "html",
    reply_to_message_id: int = None,
) -> dict:
    """Send a text message with coloured inline buttons — replaces message.reply_text()."""
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
                print(f"[styled_send] sendMessage error: {result}")
            return result


async def edit_styled(
    chat_id: int,
    message_id: int,
    reply_markup=None,
) -> dict:
    """Edit reply markup only — replaces message.edit_reply_markup()."""
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
                print(f"[styled_send] editMarkup error: {result}")
            return result