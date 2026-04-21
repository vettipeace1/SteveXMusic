# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

import asyncio
from pyrogram import enums, filters, types

from anony import app, config, db, lang
from anony.helpers import utils, buttons


# ─── HELP COMMAND (PM) ───
@app.on_message(filters.command(["help"]) & filters.private & ~app.bl_users)
@lang.language()
async def _help(_, message: types.Message):
    await message.reply_video(
        video=config.START_VDO,
        caption=message.lang["help_menu"],
        reply_markup=buttons.help_markup(message.lang),
    )


# ─── START COMMAND ───
@app.on_message(filters.command(["start"]))
@lang.language()
async def start(_, message: types.Message):

    if message.from_user.id in app.bl_users and message.from_user.id not in db.notified:
        return await message.reply_text(message.lang["bl_user_notify"])

    private = message.chat.type == enums.ChatType.PRIVATE

    # /start help
    if len(message.command) > 1 and message.command[1] == "help":
        return await _help(_, message)

    if private:
        # ── PM START ──
        _text = message.lang["start_pm"].format(
            message.from_user.first_name, app.name
        )

        await message.reply_video(
            video=config.START_VDO,
            caption=_text,
            reply_markup=buttons.start_key(message.lang, private=True),
        )

        if not await db.is_user(message.from_user.id):
            await utils.send_log(message)
            await db.add_user(message.from_user.id)

    else:
        # ── GROUP START ──
        _text = message.lang["start_gp"].format(app.name)

        key = types.InlineKeyboardMarkup(
            [
                [
                    types.InlineKeyboardButton(
                        text=message.lang["language"],
                        callback_data="language",
                    )
                ],
                [
                    types.InlineKeyboardButton(
                        text=message.lang["channel"],
                        url=config.SUPPORT_CHANNEL,
                    )
                ],
            ]
        )

        await message.reply_video(
            video=config.START_VDO,
            caption=_text,
            reply_markup=key,
            quote=True,
        )

        if not await db.is_chat(message.chat.id):
            await utils.send_log(message, True)
            await db.add_chat(message.chat.id)


# ─── OPEN LANGUAGE MENU ───
@app.on_callback_query(filters.regex("^language$"))
async def open_language(_, query: types.CallbackQuery):
    await query.message.edit_reply_markup(
        reply_markup=lang.build_lang_menu()
    )


# ─── CLOSE LANGUAGE MENU ───
@app.on_callback_query(filters.regex("^close_lang$"))
@lang.language()
async def close_lang(_, query: types.CallbackQuery):
    _lang = query.lang
    private = query.message.chat.type == enums.ChatType.PRIVATE

    if private:
        # Back to PM start buttons
        markup = buttons.start_key(_lang, private=True)
    else:
        # Back to GROUP buttons
        markup = types.InlineKeyboardMarkup(
            [
                [
                    types.InlineKeyboardButton(
                        text=_lang["language"],
                        callback_data="language",
                    )
                ],
                [
                    types.InlineKeyboardButton(
                        text=_lang["channel"],
                        url=config.SUPPORT_CHANNEL,
                    )
                ],
            ]
        )

    await query.message.edit_reply_markup(reply_markup=markup)


# ─── HELP BUTTON CLICK ───
@app.on_callback_query(filters.regex("^help$"))
@lang.language()
async def help_cb(_, query: types.CallbackQuery):
    _lang = query.lang

    await query.message.edit_reply_markup(
        reply_markup=buttons.help_markup(_lang)
    )


# ─── SETTINGS ───
@app.on_message(filters.command(["playmode", "settings"]) & filters.group & ~app.bl_users)
@lang.language()
async def settings(_, message: types.Message):

    admin_only = await db.get_play_mode(message.chat.id)
    cmd_delete = await db.get_cmd_delete(message.chat.id)
    _language = await db.get_lang(message.chat.id)

    await message.reply_text(
        text=message.lang["start_settings"].format(message.chat.title),
        reply_markup=buttons.settings_markup(
            message.lang, admin_only, cmd_delete, _language, message.chat.id
        ),
        quote=True,
    )


# ─── NEW MEMBER ───
@app.on_message(filters.new_chat_members, group=7)
@lang.language()
async def _new_member(_, message: types.Message):

    if message.chat.type != enums.ChatType.SUPERGROUP:
        return await message.chat.leave()

    await asyncio.sleep(3)

    for member in message.new_chat_members:
        if member.id == app.id:
            if await db.is_chat(message.chat.id):
                return
            await utils.send_log(message, True)
            await db.add_chat(message.chat.id)