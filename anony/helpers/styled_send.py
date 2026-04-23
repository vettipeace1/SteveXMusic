# anony/helpers/styled_send.py
# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

import html
import json
import os
import re

import aiohttp

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ── errors we silently swallow ────────────────────────────────────────────────
_IGNORED = {"message is not modified"}


def _is_ignorable(result: dict) -> bool:
    desc = result.get("description", "")
    return any(ig in desc for ig in _IGNORED)


# ── markup serialiser ─────────────────────────────────────────────────────────
def _markup(markup) -> str:
    rows = []
    for row in markup.inline_keyboard:
        btn_row = []
        for btn in row:
            d = {"text": btn.text}

            # colour / style — serialised so Telegram renders the button colour
            style = getattr(btn, "style", None)
            if style:
                d["style"] = style

            if getattr(btn, "callback_data", None) is not None:
                d["callback_data"] = btn.callback_data
            elif getattr(btn, "url", None):
                d["url"] = btn.url
            elif getattr(btn, "switch_inline_query", None) is not None:
                d["switch_inline_query"] = btn.switch_inline_query
            elif getattr(btn, "switch_inline_query_current_chat", None) is not None:
                d["switch_inline_query_current_chat"] = btn.switch_inline_query_current_chat
            elif getattr(btn, "copy_text", None) is not None:
                d["copy_text"] = {"text": btn.copy_text}

            btn_row.append(d)
        rows.append(btn_row)
    return json.dumps({"inline_keyboard": rows})


# ── HTML safety ───────────────────────────────────────────────────────────────
def _safe_html(text: str) -> str:
    """
    Escape bare &, <, > in text nodes without touching existing HTML tags.
    Fixes "can't parse entities" caused by usernames like $STEVE🦅 or
    any stray special character that breaks Telegram's HTML parser.
    """
    # Split: keep tags as-is, escape text nodes only
    parts = re.split(r"(<[^>]+>)", text)
    out = []
    for part in parts:
        if part.startswith("<") and part.endswith(">"):
            out.append(part)          # valid HTML tag — leave untouched
        else:
            out.append(html.escape(part, quote=False))  # text node — escape
    return "".join(out)


# ── API wrappers ──────────────────────────────────────────────────────────────

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
        "caption": _safe_html(caption) if parse_mode == "html" else caption,
        "parse_mode": parse_mode,
    }
    if reply_markup:
        data["reply_markup"] = _markup(reply_markup)
    if reply_to_message_id:
        data["reply_to_message_id"] = reply_to_message_id

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE}/sendVideo", data=data) as resp:
            result = await resp.json()
            if not result.get("ok") and not _is_ignorable(result):
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
        "text": _safe_html(text) if parse_mode == "html" else text,
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
            if not result.get("ok") and not _is_ignorable(result):
                print(f"[styled_send] sendMessage error: {result}")
            return result


async def edit_styled(
    chat_id: int,
    message_id: int,
    reply_markup=None,
) -> dict:
    data = {"chat_id": chat_id, "message_id": message_id}
    if reply_markup:
        data["reply_markup"] = _markup(reply_markup)

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE}/editMessageReplyMarkup", data=data) as resp:
            result = await resp.json()
            if not result.get("ok") and not _is_ignorable(result):
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
        "caption": _safe_html(caption) if parse_mode == "html" else caption,
        "parse_mode": parse_mode,
    }
    if reply_markup:
        data["reply_markup"] = _markup(reply_markup)

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE}/editMessageCaption", data=data) as resp:
            result = await resp.json()
            if not result.get("ok") and not _is_ignorable(result):
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
        "text": _safe_html(text) if parse_mode == "html" else text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    if reply_markup:
        data["reply_markup"] = _markup(reply_markup)

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE}/editMessageText", data=data) as resp:
            result = await resp.json()
            if not result.get("ok") and not _is_ignorable(result):
                print(f"[styled_send] editText error: {result}")
            return result