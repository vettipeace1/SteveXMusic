# anony/helpers/styled_send.py

import json
import os
import re
from html import escape
import aiohttp

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Harmless errors that don't need to be printed
_IGNORE_ERRORS = {"message is not modified"}


# ─────────────────────────────────────────────────────────────────
#  HTML SANITISER
#  Pyrogram's .html / mention property generates strings like:
#    <a href="tg://user?id=123">KING〽~$STEVE⊬🦅</a>
#
#  The Telegram Bot API's HTML parser rejects this with:
#    "can't parse entities: Unexpected end of name token"
#  because it tries to interpret characters like $, ~, 〽, ⊬ inside
#  an <a> tag's text as part of an HTML entity name.
#
#  Strategy (applied in order):
#   1. Extract tg:// mention links → keep name only, wrapped in <b>.
#      The Bot API does NOT support tg:// hrefs in edit/send calls.
#   2. Extract any other <a href="..."> links → keep as-is but
#      escape the inner text so special chars don't break parsing.
#   3. Escape all remaining plain text fragments (outside tags):
#      &  →  &amp;
#      <  →  &lt;
#      >  →  &gt;
#   4. Recognised safe tags (<b> <i> <u> <s> <code> <pre>
#      <blockquote>) are preserved verbatim.
#
#  This means ALL names — Arabic, Chinese, emoji, $symbols, ~tildes,
#  mixed scripts, zero-width chars — are safe to pass through.
# ─────────────────────────────────────────────────────────────────

# Tags the Bot API's HTML mode actually supports
_SAFE_OPEN  = re.compile(
    r'<(/?)(b|i|u|s|code|pre|blockquote)(\s[^>]*)?>',
    re.IGNORECASE,
)
# Full <a href="...">...</a> pattern (greedy on inner text is fine
# because we process left-to-right via re.split logic below)
_A_TAG = re.compile(
    r'<a\s+href=["\']([^"\']*)["\'][^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
_TG_HREF = re.compile(r'^tg://', re.IGNORECASE)


def _sanitise_html(text: str) -> str:
    """
    Make an HTML string safe for Telegram Bot API parse_mode=html.

    Handles every special character in usernames/titles:
    ~  $  &  <  >  "  '  〽  ⊬  emojis  Arabic  Cyrillic  etc.
    """
    if not text:
        return text

    result = []
    pos = 0

    for m in _A_TAG.finditer(text):
        start, end = m.start(), m.end()
        href, inner = m.group(1), m.group(2)

        # 1. Escape plain text before this tag
        plain = text[pos:start]
        result.append(_escape_outside_tags(plain))

        # 2. Handle the <a> tag itself
        if _TG_HREF.match(href):
            # tg:// links are NOT supported by Bot API in edit calls.
            # Convert to bold so the name is still visible.
            result.append(f"<b>{escape(inner)}</b>")
        else:
            # Regular https:// link — keep it, but escape the inner text
            safe_href = escape(href, quote=True)
            result.append(f'<a href="{safe_href}">{escape(inner)}</a>')

        pos = end

    # Remaining text after last <a> tag
    result.append(_escape_outside_tags(text[pos:]))

    return "".join(result)


def _escape_outside_tags(fragment: str) -> str:
    """
    Escape a fragment of text that may contain safe HTML tags
    (<b>, <i>, <u>, <s>, <code>, <pre>, <blockquote>) but also
    raw special characters in plain text sections.

    We split on safe tags, escape everything outside them, and
    reassemble.
    """
    if not fragment:
        return fragment

    parts = _SAFE_OPEN.split(fragment)
    # re.split with a capturing group gives:
    # [before, slash, tag, attrs, after, slash, tag, attrs, ...]
    # When there are no groups captured it's just [whole_string].
    # _SAFE_OPEN has 3 capturing groups so chunks come in groups of 4:
    # text, slash, tagname, attrs  (repeat)

    if len(parts) == 1:
        # No safe tags found — escape everything
        return _escape_text(parts[0])

    out = []
    i = 0
    while i < len(parts):
        if i % 4 == 0:
            # Plain text segment — escape it
            out.append(_escape_text(parts[i]))
        elif i % 4 == 1:
            # Slash (/ or empty) — part of tag reconstruction
            slash = parts[i]
            tagname = parts[i + 1]
            attrs = parts[i + 2] or ""
            # Reconstruct the safe tag verbatim
            out.append(f"<{slash}{tagname}{attrs}>")
            i += 2  # skip tagname and attrs, loop will +1 more
        i += 1

    return "".join(out)


def _escape_text(text: str) -> str:
    """
    Escape &, <, > in plain text (not inside any HTML tag).
    Uses html.escape which handles & → &amp;  < → &lt;  > → &gt;
    """
    return escape(text, quote=False)


# ─────────────────────────────────────────────────────────────────
#  MARKUP SERIALISER
# ─────────────────────────────────────────────────────────────────

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
    if any(e in desc for e in _IGNORE_ERRORS):
        return
    print(f"[styled_send] {fn_name} error: {result}")


# ─────────────────────────────────────────────────────────────────
#  PUBLIC API
# ─────────────────────────────────────────────────────────────────

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
        "caption": _sanitise_html(caption),
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
        "text": _sanitise_html(text),
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