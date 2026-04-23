# anony/helpers/styled_send.py

import json
import os
from html import escape, unescape
from html.parser import HTMLParser
import aiohttp

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

_IGNORE_ERRORS = {"message is not modified"}

# Tags the Telegram Bot API HTML mode supports
_BOT_API_SAFE_TAGS = {
    "b", "strong",
    "i", "em",
    "u", "ins",
    "s", "strike", "del",
    "code", "pre",
    "blockquote",
    "a",
}


# ─────────────────────────────────────────────────────────────────
#  HTML SANITISER
#
#  Converts Pyrogram HTML (which may contain tg:// mention links and
#  unescaped special chars in usernames) into safe Bot API HTML.
#
#  Key behaviours:
#   • tg:// mention links  →  plain text only (no tag wrapping)
#     e.g. <a href="tg://user?id=123">KING〽~$STEVE⊬🦅</a>
#          → KING〽~$STEVE⊬🦅  (just the name, no bold, no link)
#   • https:// links       →  kept as <a href="...">text</a>
#   • Safe tags (<b><i><u><s><code><pre><blockquote>) → kept
#   • All text nodes       →  html.escape()'d  (handles every
#     script, emoji, symbol, ~$〽⊬ etc.)
#   • Unsupported tags     →  dropped, inner text kept as plain text
# ─────────────────────────────────────────────────────────────────

class _Sanitiser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self._out = []
        # stack entries: (tagname, is_tg_link, should_emit_close_tag)
        self._stack = []
        # when True we suppress output (inside unsupported tag)
        # — actually we keep text, just don't emit the tags themselves
        self._in_tg_link = False  # inside a tg:// <a> tag

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        if t not in _BOT_API_SAFE_TAGS:
            self._stack.append((t, False, False))
            return

        if t == "a":
            href = dict(attrs).get("href", "")
            if href.lower().startswith("tg://"):
                # tg:// not supported — emit name as plain text only
                self._in_tg_link = True
                self._stack.append(("a", True, False))
            else:
                safe_href = escape(href, quote=True)
                self._out.append(f'<a href="{safe_href}">')
                self._stack.append(("a", False, True))
        else:
            self._out.append(f"<{t}>")
            self._stack.append((t, False, True))

    def handle_endtag(self, tag):
        t = tag.lower()
        for i in range(len(self._stack) - 1, -1, -1):
            entry = self._stack[i]
            if entry[0] == t:
                self._stack.pop(i)
                _, is_tg, emit_close = entry
                if is_tg:
                    self._in_tg_link = False
                elif emit_close:
                    self._out.append(f"</{t}>")
                return

    def handle_data(self, data):
        # Always escape text content — handles ALL special chars
        self._out.append(escape(data, quote=False))

    def handle_entityref(self, name):
        # Named entity e.g. &amp; &lt; — pass through
        self._out.append(f"&{name};")

    def handle_charref(self, name):
        # Numeric entity e.g. &#123; &#xAB; — pass through
        self._out.append(f"&#{name};")

    def result(self) -> str:
        return "".join(self._out)


def _sanitise_html(text: str) -> str:
    """
    Make any HTML string safe for Telegram Bot API parse_mode=html.

    Supports ALL usernames/names regardless of characters:
    ~  $  &  <  >  "  '  〽  ⊬  🦅  emojis  Arabic  Cyrillic
    Chinese  Tamil  mixed scripts  zero-width chars  etc.

    tg:// mention links are stripped to plain text (name only, no tag).
    https:// links are preserved.
    """
    if not text:
        return text
    p = _Sanitiser()
    p.feed(text)
    return p.result()


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