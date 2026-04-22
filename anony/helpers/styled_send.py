# anony/utils/styled_send.py
#
# Since kurigram (MTProto) does not yet support Bot API 9.4 button styles,
# this helper sends messages with styled buttons directly via the HTTP Bot API.
# Your bot still runs on kurigram for everything else — only styled-button
# messages go through this helper.
#
# Usage example (in your handlers):
#
#   from anony.utils.styled_send import send_styled, edit_styled
#
#   await send_styled(
#       chat_id=message.chat.id,
#       text="Welcome!",
#       reply_markup=inline.start_key(lang)   ← your existing Inline object works!
#   )
#
# The inline.start_key() etc. still build the keyboard exactly as before.
# This file converts the kurigram InlineKeyboardMarkup into the JSON format
# the HTTP Bot API expects, including the style= field.

import json
import aiohttp
from anony import config   # your BOT_TOKEN lives here


BOT_API_URL = f"https://api.telegram.org/bot{config.BOT_TOKEN}"


def _button_to_dict(btn) -> dict:
    """Convert a single kurigram InlineKeyboardButton to a Bot API dict."""
    d = {"text": btn.text}

    # style (color) — Bot API 9.4 field
    if getattr(btn, "style", None):
        d["style"] = btn.style

    # action fields
    if getattr(btn, "callback_data", None) is not None:
        d["callback_data"] = btn.callback_data
    elif getattr(btn, "url", None):
        d["url"] = btn.url
    elif getattr(btn, "switch_inline_query", None) is not None:
        d["switch_inline_query"] = btn.switch_inline_query
    elif getattr(btn, "switch_inline_query_current_chat", None) is not None:
        d["switch_inline_query_current_chat"] = btn.switch_inline_query_current_chat

    return d


def _markup_to_dict(markup) -> dict:
    """Convert a kurigram InlineKeyboardMarkup to a Bot API reply_markup dict."""
    rows = []
    for row in markup.inline_keyboard:
        rows.append([_button_to_dict(btn) for btn in row])
    return {"inline_keyboard": rows}


async def send_styled(
    chat_id: int,
    text: str,
    reply_markup=None,
    parse_mode: str = "html",
    disable_web_page_preview: bool = True,
    reply_to_message_id: int = None,
) -> dict:
    """Send a message with styled (coloured) inline buttons via HTTP Bot API."""
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_web_page_preview,
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(_markup_to_dict(reply_markup))
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BOT_API_URL}/sendMessage", data=payload) as resp:
            return await resp.json()


async def edit_styled(
    chat_id: int,
    message_id: int,
    text: str,
    reply_markup=None,
    parse_mode: str = "html",
    disable_web_page_preview: bool = True,
) -> dict:
    """Edit a message with styled (coloured) inline buttons via HTTP Bot API."""
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_web_page_preview,
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(_markup_to_dict(reply_markup))

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BOT_API_URL}/editMessageText", data=payload) as resp:
            return await resp.json()


async def answer_callback_styled(
    callback_query_id: str,
    text: str = None,
    show_alert: bool = False,
) -> dict:
    """Answer a callback query (use this when your handler uses send_styled)."""
    payload = {
        "callback_query_id": callback_query_id,
        "show_alert": show_alert,
    }
    if text:
        payload["text"] = text

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BOT_API_URL}/answerCallbackQuery", data=payload) as resp:
            return await resp.json()