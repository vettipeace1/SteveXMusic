# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

# ══════════════════════════════════════════════════════════════════════════════
#  HOW COLOUR BUTTONS WORK IN THIS SETUP
#  ─────────────────────────────────────
#  kurigram (MTProto) does not yet support Bot API 9.4 style= field.
#  So we:
#    1. Store style as a plain Python attribute on each button object here.
#    2. Use anony/utils/styled_send.py to send/edit messages that need colours.
#       That helper sends directly to Telegram's HTTP Bot API, which supports style=.
#
#  Bot API 9.4 style values:
#    style="primary"  →  🔵 BLUE
#    style="success"  →  🟢 GREEN
#    style="danger"   →  🔴 RED
#
#  Colour rules:
#   1) Add me to your group  → 🟢 GREEN   (style="success")
#   2) Help                  → 🔵 BLUE    (style="primary")
#   3) Source                → 🔴 RED     (style="danger")
#   4) All Back buttons      → 🟢 GREEN   (style="success")
#   5) All Close buttons     → 🔴 RED     (style="danger")
#   6) Timer during playing  → 🔴 RED     (style="danger")
# ══════════════════════════════════════════════════════════════════════════════

from pyrogram import types

from anony import app, config, lang
from anony.core.lang import lang_codes


# ── Safe button builder ───────────────────────────────────────────────────────
# Creates an InlineKeyboardButton and stores style as a plain Python attribute.
# styled_send.py reads btn.style when building the HTTP payload for colours.

def _ikb(text: str, *, style: str = None, **kwargs) -> types.InlineKeyboardButton:
    btn = types.InlineKeyboardButton(text=text, **kwargs)
    btn.style = style  # plain attribute — not sent by kurigram, read by styled_send.py
    return btn


class Inline:
    def __init__(self):
        self.ikm = types.InlineKeyboardMarkup

    def cancel_dl(self, text) -> types.InlineKeyboardMarkup:
        return self.ikm([[_ikb(text, callback_data="cancel_dl")]])

    def controls(
        self,
        chat_id: int,
        status: str = None,
        timer: str = None,
        remove: bool = False,
    ) -> types.InlineKeyboardMarkup:
        keyboard = []

        if status:
            keyboard.append(
                [_ikb(status, callback_data=f"controls status {chat_id}")]
            )
        elif timer:
            # Rule 6: Timer → 🔴 RED
            keyboard.append(
                [_ikb(timer, style="danger", callback_data=f"controls status {chat_id}")]
            )

        if not remove:
            keyboard.append(
                [
                    _ikb("▷",   callback_data=f"controls resume {chat_id}"),
                    _ikb("II",  callback_data=f"controls pause {chat_id}"),
                    _ikb("⥁",   callback_data=f"controls replay {chat_id}"),
                    _ikb("‣‣I", callback_data=f"controls skip {chat_id}"),
                    _ikb("▢",   callback_data=f"controls stop {chat_id}"),
                ]
            )
        return self.ikm(keyboard)

    def help_markup(
        self, _lang: dict, back: bool = False
    ) -> types.InlineKeyboardMarkup:
        if back:
            rows = [
                [
                    _ikb(_lang["back"],  style="success", callback_data="help back"),   # Rule 4: 🟢
                    _ikb(_lang["close"], style="danger",  callback_data="help close"),  # Rule 5: 🔴
                ]
            ]
        else:
            cbs = ["admins", "auth", "blist", "lang", "ping", "play", "queue", "stats", "sudo"]
            buttons = [
                _ikb(_lang[f"help_{i}"], callback_data=f"help {cb}")
                for i, cb in enumerate(cbs)
            ]
            rows = [buttons[i : i + 3] for i in range(0, len(buttons), 3)]

        return self.ikm(rows)

    def lang_markup(self, _lang: str) -> types.InlineKeyboardMarkup:
        langs = lang.get_languages()
        buttons = [
            _ikb(
                f"{name} ({code}) {'✔️' if code == _lang else ''}",
                callback_data=f"lang_change {code}",
            )
            for code, name in langs.items()
        ]
        rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
        return self.ikm(rows)

    def ping_markup(self, text: str) -> types.InlineKeyboardMarkup:
        return self.ikm([[_ikb(text, url=config.SUPPORT_CHAT)]])

    def play_queued(
        self, chat_id: int, item_id: str, _text: str
    ) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [[_ikb(_text, callback_data=f"controls force {chat_id} {item_id}")]]
        )

    def queue_markup(
        self, chat_id: int, _text: str, playing: bool
    ) -> types.InlineKeyboardMarkup:
        _action = "pause" if playing else "resume"
        return self.ikm(
            [[_ikb(_text, callback_data=f"controls {_action} {chat_id} q")]]
        )

    def settings_markup(
        self, lang: dict, admin_only: bool, cmd_delete: bool, language: str, chat_id: int
    ) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    _ikb(lang["play_mode"] + " ➜", callback_data="settings"),
                    _ikb(admin_only, callback_data="settings play"),
                ],
                [
                    _ikb(lang["cmd_delete"] + " ➜", callback_data="settings"),
                    _ikb(cmd_delete, callback_data="settings delete"),
                ],
                [
                    _ikb(lang["language"] + " ➜", callback_data="settings"),
                    _ikb(lang_codes[language], callback_data="language"),
                ],
            ]
        )

    def start_key(
        self, lang: dict, private: bool = False
    ) -> types.InlineKeyboardMarkup:
        rows = [
            # Rule 1: Add me → 🟢 GREEN
            [_ikb(lang["add_me"],
                  style="success",
                  url=f"https://t.me/{app.username}?startgroup=true")],
            # Rule 2: Help → 🔵 BLUE
            [_ikb(lang["help"],
                  style="primary",
                  callback_data="help")],
            # Support + Channel → default
            [
                _ikb(lang["support"], url=config.SUPPORT_CHAT),
                _ikb(lang["channel"], url=config.SUPPORT_CHANNEL),
            ],
        ]

        if private:
            # Rule 3: Source → 🔴 RED
            rows += [
                [_ikb(lang["source"],
                      style="danger",
                      url="https://t.me/vettipeace")]
            ]
        else:
            rows += [[_ikb(lang["language"], callback_data="language")]]

        return self.ikm(rows)

    def start_key_group(self, lang: dict) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [_ikb(lang["help"],     style="primary", callback_data="help")],
                [_ikb(lang["language"], callback_data="language")],
            ]
        )

    def yt_key(self, link: str) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    _ikb("❐", copy_text=link),
                    _ikb("Youtube", url=link),
                ],
            ]
        )