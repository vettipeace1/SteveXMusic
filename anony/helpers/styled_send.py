# anony/helpers/styled_send.py

import json
import os
import re
import aiohttp

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"


def _sanitise_html(text: str) -> str:
    """
    Fix bare '&' characters that are NOT part of a valid HTML entity.

    Pyrogram's .html property wraps mentions as:
        <a href="tg://user?id=123">NAME</a>
    If NAME contains a raw '&' (e.g. "AT&T"), Telegram's Bot API rejects
    it with:
        Bad Request: can't parse entities: Unexpected end of name token

    This regex escapes only the bare '&' that are not already an entity,
    leaving &amp; &lt; &gt; &#123; etc. untouched.
    """
    if not text:
        return text
    return re.sub(r"&(?!(?:#\d+|#x[\da-fA-F]+|[a-zA-Z]\w*);)", "&amp;", text)


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


def _is_not_modified(result: dict) -> bool:
    """Returns True for the harmless 'message is not modified' error."""
    return (
        not result.get("ok")
        and result.get("error_code") == 400
        and "message is not modified" in result.get("description", "")
    )


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
        "caption": _sanitise_html(caption),
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

    data = {
        "chat_id": chat_id,
        "text": _sanitise_html(text),
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

    data = {
        "chat_id": chat_id,
        "message_id": message_id,
    }

    if reply_markup:
        data["reply_markup"] = _markup(reply_markup)

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE}/editMessageReplyMarkup", data=data) as resp:
            result = await resp.json()

            # Silence the harmless "not modified" noise
            if not result.get("ok") and not _is_not_modified(result):
                print(f"[styled_send] editMarkup error: {result}")

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
        "caption": _sanitise_html(caption),
        "parse_mode": parse_mode,
    }

    if reply_markup:
        data["reply_markup"] = _markup(reply_markup)

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE}/editMessageCaption", data=data) as resp:
            result = await resp.json()

            if not result.get("ok") and not _is_not_modified(result):
                print(f"[styled_send] editCaption error: {result}")

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
        "text": _sanitise_html(text),
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    if reply_markup:
        data["reply_markup"] = _markup(reply_markup)

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE}/editMessageText", data=data) as resp:
            result = await resp.json()

            if not result.get("ok") and not _is_not_modified(result):
                print(f"[styled_send] editText error: {result}")

            return result