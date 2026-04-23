# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

from pyrogram import types

from anony import app, config, lang
from anony.core.lang import lang_codes


def _ikb(text: str, *, style: str = None, **kwargs) -> types.InlineKeyboardButton:
    """Create an InlineKeyboardButton and attach an optional style (colour) attr."""
    btn = types.InlineKeyboardButton(text=text, **kwargs)
    btn.style = style
    return btn


class Inline:
    def __init__(self):
        self.ikm = types.InlineKeyboardMarkup

    def ikb(self, text: str, *, style: str = None, **kwargs) -> types.InlineKeyboardButton:
        return _ikb(text, style=style, **kwargs)

    # ── cancel download ───────────────────────────────────────────────────────
    def cancel_dl(self, text) -> types.InlineKeyboardMarkup:
        return self.ikm([[_ikb(text, callback_data="cancel_dl")]])

    # ── playback controls ─────────────────────────────────────────────────────
    def controls(
        self,
        chat_id: int,
        status: str = None,
        timer: str = None,
        remove: bool = False,
    ) -> types.InlineKeyboardMarkup:
        keyboard = []

        if status:
            # "Stream paused" / "Skipped" / etc. → 🔴 RED banner
            keyboard.append(
                [_ikb(status, style="danger", callback_data=f"controls status {chat_id}")]
            )
        elif timer:
            # Playback timer → 🟢 GREEN banner
            keyboard.append(
                [_ikb(timer, style="success", callback_data=f"controls status {chat_id}")]
            )

        if not remove:
            # Control row — plain Unicode symbols, no special HTML, no names that
            # could trip the entity parser
            keyboard.append(
                [
                    _ikb("▷",   style="primary",  callback_data=f"controls resume {chat_id}"),
                    _ikb("II",   style="secondary", callback_data=f"controls pause  {chat_id}"),
                    _ikb("⥁",   callback_data=f"controls replay {chat_id}"),
                    _ikb("⏭",   callback_data=f"controls skip   {chat_id}"),
                    _ikb("▢",   style="danger",   callback_data=f"controls stop   {chat_id}"),
                ]
            )
        return self.ikm(keyboard)

    # ── help menu ─────────────────────────────────────────────────────────────
    def help_markup(
        self, _lang: dict, back: bool = False
    ) -> types.InlineKeyboardMarkup:
        if back:
            rows = [
                [
                    _ikb(_lang["back"],  style="success", callback_data="help back"),   # 🟢
                    _ikb(_lang["close"], style="danger",  callback_data="help close"),  # 🔴
                ]
            ]
        else:
            cbs = ["admins", "auth", "blist", "lang", "ping", "play", "queue", "stats", "sudo"]
            btns = [
                _ikb(_lang[f"help_{i}"], callback_data=f"help {cb}")
                for i, cb in enumerate(cbs)
            ]
            rows = [btns[i : i + 3] for i in range(0, len(btns), 3)]
        return self.ikm(rows)

    # ── language picker ───────────────────────────────────────────────────────
    def lang_markup(self, _lang: str) -> types.InlineKeyboardMarkup:
        langs = lang.get_languages()
        btns = [
            _ikb(
                f"{name} ({code}) {'✔️' if code == _lang else ''}",
                callback_data=f"lang_change {code}",
            )
            for code, name in langs.items()
        ]
        rows = [btns[i : i + 2] for i in range(0, len(btns), 2)]
        return self.ikm(rows)

    # ── ping ──────────────────────────────────────────────────────────────────
    def ping_markup(self, text: str) -> types.InlineKeyboardMarkup:
        return self.ikm([[_ikb(text, url=config.SUPPORT_CHAT)]])

    # ── "Play Now" queued button → 🔵 BLUE ───────────────────────────────────
    def play_queued(
        self, chat_id: int, item_id: str, _text: str
    ) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [[_ikb(_text, style="primary", callback_data=f"controls force {chat_id} {item_id}")]]
        )

    # ── queue pause/resume toggle ─────────────────────────────────────────────
    def queue_markup(
        self, chat_id: int, _text: str, playing: bool
    ) -> types.InlineKeyboardMarkup:
        _action = "pause" if playing else "resume"
        style   = "danger" if playing else "success"   # red=pause, green=resume
        return self.ikm(
            [[_ikb(_text, style=style, callback_data=f"controls {_action} {chat_id} q")]]
        )

    # ── settings ──────────────────────────────────────────────────────────────
    def settings_markup(
        self, lang: dict, admin_only: bool, cmd_delete: bool, language: str, chat_id: int
    ) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    _ikb(lang["play_mode"] + " ➜", callback_data="settings"),
                    _ikb(str(admin_only),           callback_data="settings play"),
                ],
                [
                    _ikb(lang["cmd_delete"] + " ➜", callback_data="settings"),
                    _ikb(str(cmd_delete),            callback_data="settings delete"),
                ],
                [
                    _ikb(lang["language"] + " ➜", callback_data="settings"),
                    _ikb(lang_codes[language],     callback_data="language"),
                ],
            ]
        )

    # ── start / PM buttons ────────────────────────────────────────────────────
    def start_key(
        self, lang: dict, private: bool = False
    ) -> types.InlineKeyboardMarkup:
        rows = [
            [_ikb(lang["add_me"], style="primary",
                  url=f"https://t.me/{app.username}?startgroup=true")],   # 🔵
            [_ikb(lang["help"],   style="success", callback_data="help")], # 🟢
            [
                _ikb(lang["support"], url=config.SUPPORT_CHAT),
                _ikb(lang["channel"], url=config.SUPPORT_CHANNEL),
            ],
        ]
        if private:
            rows += [[_ikb(lang["source"], style="danger",
                           url="https://t.me/vettipeace")]]                # 🔴
        else:
            rows += [[_ikb(lang["language"], callback_data="language")]]
        return self.ikm(rows)

    def start_key_group(self, lang: dict) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [_ikb(lang["help"], style="success", callback_data="help")], # 🟢
                [_ikb(lang["language"], callback_data="language")],
            ]
        )

    # ── YouTube link button ───────────────────────────────────────────────────
    def yt_key(self, link: str) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    _ikb("❐",       copy_text=link),
                    _ikb("Youtube", url=link),
                ],
            ]
        )