# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

# ══════════════════════════════════════════════════════════════════════════════
#  Pyrogram does NOT support the Bot API 9.4 `style` field natively yet.
#  We use Pyrogram's raw TL layer directly via:
#
#    from pyrogram.raw.types import (
#        KeyboardButtonCallback,
#        KeyboardButtonUrl,
#        KeyboardButtonColor,         ← wraps any button with a colour
#        ReplyInlineMarkup,
#        KeyboardButtonRow,
#    )
#
#  KeyboardButtonColor flags:
#    .green       = True  →  🟢 GREEN
#    .blue        = True  →  🔵 BLUE  (actually "primary")
#    .red         = True  →  🔴 RED
#    (all False)          →  default (desaturated navy)
#
#  IMPORTANT: When using raw buttons you must send the message with
#  reply_markup passed as a raw ReplyInlineMarkup object, NOT as
#  types.InlineKeyboardMarkup. The helper send_raw_msg() below shows how.
#
#  For places that already use app.send_message / message.reply_text etc,
#  replace reply_markup=... with the raw ReplyInlineMarkup returned here.
# ══════════════════════════════════════════════════════════════════════════════

from pyrogram import types
from pyrogram.raw import types as raw_types

from anony import app, config, lang
from anony.core.lang import lang_codes


# ── Colour helper ─────────────────────────────────────────────────────────────

def _color(button, *, green=False, blue=False, red=False):
    """Wrap a raw button with KeyboardButtonColor to apply a colour."""
    return raw_types.KeyboardButtonColor(
        button=button,
        green=green,
        blue=blue,
        red=red,
    )

def _row(*buttons):
    return raw_types.KeyboardButtonRow(buttons=list(buttons))

def _markup(*rows):
    return raw_types.ReplyInlineMarkup(rows=list(rows))

def _cb(text, data: str):
    """Callback button."""
    return raw_types.KeyboardButtonCallback(
        text=text,
        data=data.encode(),
    )

def _url(text, url: str):
    """URL button."""
    return raw_types.KeyboardButtonUrl(text=text, url=url)

def _copy(text, copy_text: str):
    """Copy-text button."""
    return raw_types.KeyboardButtonCopy(text=text, copy_text=copy_text)


# ══════════════════════════════════════════════════════════════════════════════
#  COLOUR RULES:
#   1) Add me to your group  → 🟢 GREEN
#   2) Help                  → 🔵 BLUE
#   3) Source                → 🔴 RED
#   4) All Back buttons      → 🟢 GREEN
#   5) All Close buttons     → 🔴 RED
#   6) Timer during playing  → 🔴 RED
#   Everything else          → default (no colour wrapper)
# ══════════════════════════════════════════════════════════════════════════════

class Inline:
    def __init__(self):
        # Keep these for parts of the code that still use normal Pyrogram types
        self.ikm = types.InlineKeyboardMarkup
        self.ikb = types.InlineKeyboardButton

    # ── cancel download (no colour needed) ───────────────────────────────────
    def cancel_dl(self, text):
        return _markup(
            _row(_cb(text, "cancel_dl"))
        )

    # ── playback controls ─────────────────────────────────────────────────────
    def controls(
        self,
        chat_id: int,
        status: str = None,
        timer: str = None,
        remove: bool = False,
    ):
        rows = []

        if status:
            # Normal status → default colour
            rows.append(_row(_cb(status, f"controls status {chat_id}")))
        elif timer:
            # Rule 6: Timer → RED
            rows.append(
                _row(
                    _color(
                        _cb(timer, f"controls status {chat_id}"),
                        red=True,
                    )
                )
            )

        if not remove:
            rows.append(
                _row(
                    _cb("▷",   f"controls resume {chat_id}"),
                    _cb("II",  f"controls pause {chat_id}"),
                    _cb("⥁",   f"controls replay {chat_id}"),
                    _cb("‣‣I", f"controls skip {chat_id}"),
                    _cb("▢",   f"controls stop {chat_id}"),
                )
            )

        return _markup(*rows)

    # ── help menu ─────────────────────────────────────────────────────────────
    def help_markup(self, _lang: dict, back: bool = False):
        if back:
            return _markup(
                _row(
                    # Rule 4: Back → GREEN
                    _color(_cb(_lang["back"],  "help back"),  green=True),
                    # Rule 5: Close → RED
                    _color(_cb(_lang["close"], "help close"), red=True),
                )
            )
        else:
            cbs = ["admins", "auth", "blist", "lang", "ping", "play", "queue", "stats", "sudo"]
            btns = [
                _cb(_lang[f"help_{i}"], f"help {cb}")
                for i, cb in enumerate(cbs)
            ]
            rows = [
                _row(*btns[i : i + 3])
                for i in range(0, len(btns), 3)
            ]
            return _markup(*rows)

    # ── language picker ───────────────────────────────────────────────────────
    def lang_markup(self, _lang: str):
        langs = lang.get_languages()
        btns = [
            _cb(
                f"{name} ({code}) {'✔️' if code == _lang else ''}",
                f"lang_change {code}",
            )
            for code, name in langs.items()
        ]
        rows = [_row(*btns[i : i + 2]) for i in range(0, len(btns), 2)]
        return _markup(*rows)

    # ── ping button ───────────────────────────────────────────────────────────
    def ping_markup(self, text: str):
        return _markup(_row(_url(text, config.SUPPORT_CHAT)))

    # ── play now button ───────────────────────────────────────────────────────
    def play_queued(self, chat_id: int, item_id: str, _text: str):
        return _markup(
            _row(_cb(_text, f"controls force {chat_id} {item_id}"))
        )

    # ── queue pause/resume button ─────────────────────────────────────────────
    def queue_markup(self, chat_id: int, _text: str, playing: bool):
        _action = "pause" if playing else "resume"
        return _markup(
            _row(_cb(_text, f"controls {_action} {chat_id} q"))
        )

    # ── settings ──────────────────────────────────────────────────────────────
    def settings_markup(
        self, lang: dict, admin_only: bool, cmd_delete: bool, language: str, chat_id: int
    ):
        return _markup(
            _row(
                _cb(lang["play_mode"] + " ➜", "settings"),
                _cb(admin_only, "settings play"),
            ),
            _row(
                _cb(lang["cmd_delete"] + " ➜", "settings"),
                _cb(cmd_delete, "settings delete"),
            ),
            _row(
                _cb(lang["language"] + " ➜", "settings"),
                _cb(lang_codes[language], "language"),
            ),
        )

    # ── /start private ────────────────────────────────────────────────────────
    def start_key(self, lang: dict, private: bool = False):
        rows = [
            # Rule 1: Add me → GREEN
            _row(
                _color(
                    _url(lang["add_me"], f"https://t.me/{app.username}?startgroup=true"),
                    green=True,
                )
            ),
            # Rule 2: Help → BLUE
            _row(
                _color(_cb(lang["help"], "help"), blue=True)
            ),
            # Support + Channel → default
            _row(
                _url(lang["support"], config.SUPPORT_CHAT),
                _url(lang["channel"], config.SUPPORT_CHANNEL),
            ),
        ]

        if private:
            # Rule 3: Source → RED
            rows.append(
                _row(
                    _color(
                        _url(lang["source"], "https://t.me/vettipeace"),
                        red=True,
                    )
                )
            )
        else:
            # Language → default
            rows.append(_row(_cb(lang["language"], "language")))

        return _markup(*rows)

    # ── /start group (Help BLUE + Language default) ───────────────────────────
    def start_key_group(self, lang: dict):
        return _markup(
            # Rule 2: Help → BLUE
            _row(_color(_cb(lang["help"], "help"), blue=True)),
            # Language → default
            _row(_cb(lang["language"], "language")),
        )

    # ── YouTube link button ───────────────────────────────────────────────────
    def yt_key(self, link: str):
        return _markup(
            _row(
                _copy("❐", link),
                _url("Youtube", link),
            )
        )