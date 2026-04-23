# anony/helpers/styled_send.py

import json
import os
import aiohttp

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

# 🔥 reuse session (important for performance)
_session: aiohttp.ClientSession | None = None


async def _get_session():
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession()
    return _session


def _markup(markup) -> str:
    rows = []

    for row in markup.inline_keyboard:
        btn_row = []

        for btn in row:
            d = {"text": btn.text}

            # ✅ STYLE SUPPORT
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


# ─────────────────────────────────────────────
# 🔥 CORE REQUEST HANDLER (handles all errors)
# ─────────────────────────────────────────────

async def _post(method: str, data: dict) -> dict:
    session = await _get_session()

    try:
        async with session.post(f"{BASE}/{method}", data=data) as resp:
            result = await resp.json()

            if not result.get("ok"):
                desc = result.get("description", "")

                # ✅ IGNORE SAFE ERRORS
                if "message is not modified" in desc:
                    return result
                if "query is too old" in desc:
                    return result

                print(f"[styled_send] {method} error:", result)

            return result

    except Exception as e:
        print(f"[styled_send] {method} exception:", e)
        return {"ok": False}


# ─────────────────────────────────────────────
# SEND FUNCTIONS
# ─────────────────────────────────────────────

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

    return await _post("sendMessage", data)


async def send_styled_photo(
    chat_id: int,
    photo: str,
    caption: str,
    reply_markup=None,
    parse_mode: str = "html",
) -> dict:

    data = {
        "chat_id": chat_id,
        "photo": photo,
        "caption": caption,
        "parse_mode": parse_mode,
    }

    if reply_markup:
        data["reply_markup"] = _markup(reply_markup)

    return await _post("sendPhoto", data)


async def send_styled_video(
    chat_id: int,
    video: str,
    caption: str,
    reply_markup=None,
    parse_mode: str = "html",
) -> dict:

    data = {
        "chat_id": chat_id,
        "video": video,
        "caption": caption,
        "parse_mode": parse_mode,
    }

    if reply_markup:
        data["reply_markup"] = _markup(reply_markup)

    return await _post("sendVideo", data)


# ─────────────────────────────────────────────
# EDIT FUNCTIONS
# ─────────────────────────────────────────────

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

    return await _post("editMessageReplyMarkup", data)


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

    return await _post("editMessageText", data)


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

    return await _post("editMessageCaption", data)