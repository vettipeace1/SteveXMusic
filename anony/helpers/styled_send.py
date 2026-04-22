# anony/helpers/styled_send.py
#
# Sends messages/videos with coloured buttons via HTTP Bot API.
# kurigram (MTProto) ignores style= — HTTP Bot API respects it.
# Uses your existing BOT_TOKEN — no new variable needed.

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
            # style= stored as plain attribute by _ikb() in _inline.py
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
    """Send a video with coloured buttons. Replaces message.reply_video()."""
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
    """Send a text message with coloured buttons. Replaces message.reply_text()."""
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
    caption: str = None,
    text: str = None,
    parse_mode: str = "html",
) -> dict:
    """
    Edit an existing message with coloured buttons.

    - If caption= given  → editMessageCaption  (for video/photo messages)
    - If text= given     → editMessageText     (for plain text messages)
    - Otherwise          → editMessageReplyMarkup only (markup-only edit)

    Always passes the styled reply_markup so colours are preserved.
    """
    markup_json = _markup(reply_markup) if reply_markup else None

    base_data = {
        "chat_id": chat_id,
        "message_id": message_id,
    }
    if markup_json:
        base_data["reply_markup"] = markup_json

    async with aiohttp.ClientSession() as session:

        if caption is not None:
            # Video / photo message — edit caption + markup
            data = {**base_data, "caption": caption, "parse_mode": parse_mode}
            async with session.post(f"{BASE}/editMessageCaption", data=data) as resp:
                result = await resp.json()
                if not result.get("ok"):
                    print(f"[styled_send] editMessageCaption error: {result}")
                return result

        elif text is not None:
            # Plain text message — edit text + markup
            data = {
                **base_data,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            }
            async with session.post(f"{BASE}/editMessageText", data=data) as resp:
                result = await resp.json()
                if not result.get("ok"):
                    print(f"[styled_send] editMessageText error: {result}")
                return result

        else:
            # Markup-only edit (no text change)
            async with session.post(f"{BASE}/editMessageReplyMarkup", data=base_data) as resp:
                result = await resp.json()
                if not result.get("ok"):
                    print(f"[styled_send] editMessageReplyMarkup error: {result}")
                return result