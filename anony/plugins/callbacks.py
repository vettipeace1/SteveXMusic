# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

import asyncio
import re

from pyrogram import enums, errors, filters, types

from anony import anon, app, config, db, lang, queue, tg, yt
from anony.helpers import admin_check, buttons, can_manage_vc, utils
from anony.helpers.styled_send import (
    edit_styled,
    edit_caption_styled,
    edit_text_styled,
    send_styled,
    send_styled_video,
)


# ─── CANCEL DOWNLOAD ───
@app.on_callback_query(filters.regex("cancel_dl") & ~app.bl_users)
@lang.language()
async def cancel_dl(_, query: types.CallbackQuery):
    await query.answer()
    await tg.cancel(query)


# ─── MUSIC PLAYER CONTROLS (all go through styled_send so colours work in groups) ───
@app.on_callback_query(filters.regex("controls") & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _controls(_, query: types.CallbackQuery):
    args = query.data.split()
    action, chat_id = args[1], int(args[2])
    qaction = len(args) == 4
    user = query.from_user.mention

    if not await db.get_call(chat_id):
        try:
            return await query.answer(query.lang["not_playing"], show_alert=True)
        except errors.QueryIdInvalid:
            try:
                await query.message.delete()
            except Exception:
                pass
            return

    if action == "status":
        return await query.answer()
    await query.answer(query.lang["processing"], show_alert=True)

    if action == "pause":
        if not await db.playing(chat_id):
            return await query.answer(
                query.lang["play_already_paused"], show_alert=True
            )
        await anon.pause(chat_id)
        if qaction:
            # queue view — only markup (editMessageReplyMarkup) — already styled
            return await edit_styled(
                chat_id=chat_id,
                message_id=query.message.id,
                reply_markup=buttons.queue_markup(chat_id, query.lang["paused"], False),
            )
        status = query.lang["paused"]
        reply = query.lang["play_paused"].format(user)

    elif action == "resume":
        if await db.playing(chat_id):
            return await query.answer(query.lang["play_not_paused"], show_alert=True)
        await anon.resume(chat_id)
        if qaction:
            return await edit_styled(
                chat_id=chat_id,
                message_id=query.message.id,
                reply_markup=buttons.queue_markup(chat_id, query.lang["playing"], True),
            )
        reply = query.lang["play_resumed"].format(user)
        status = None

    elif action == "skip":
        await anon.play_next(chat_id)
        status = query.lang["skipped"]
        reply = query.lang["play_skipped"].format(user)

    elif action == "force":
        pos, media = queue.check_item(chat_id, args[3])
        if not media or pos == -1:
            return await query.edit_message_text(query.lang["play_expired"])

        m_id = queue.get_current(chat_id).message_id
        queue.force_add(chat_id, media, remove=pos)
        try:
            await app.delete_messages(
                chat_id=chat_id, message_ids=[m_id, media.message_id], revoke=True
            )
            media.message_id = None
        except Exception:
            pass

        msg = await app.send_message(chat_id=chat_id, text=query.lang["play_next"])
        if not media.file_path:
            media.file_path = await yt.download(media.id, video=media.video)
        media.message_id = msg.id
        return await anon.play_media(chat_id, msg, media)

    elif action == "replay":
        media = queue.get_current(chat_id)
        media.user = user
        await anon.replay(chat_id)
        status = query.lang["replayed"]
        reply = query.lang["play_replayed"].format(user)

    elif action == "stop":
        await anon.stop(chat_id)
        status = query.lang["stopped"]
        reply = query.lang["play_stopped"].format(user)

    try:
        if action in ["skip", "replay", "stop"]:
            # Send a plain reply then delete the old player message.
            # Use send_styled so even this text reply gets raw-API delivery.
            await send_styled(
                chat_id=chat_id,
                text=reply,
                reply_to_message_id=query.message.id,
            )
            await query.message.delete()
        else:
            # pause / resume — edit the existing player message in-place
            # Strip any old blockquote status line, append the new one
            mtext = re.sub(
                r"\n\n<blockquote>.*?</blockquote>",
                "",
                query.message.caption.html
                if query.message.caption
                else query.message.text.html,
                flags=re.DOTALL,
            )
            keyboard = buttons.controls(
                chat_id, status=status if action != "resume" else None
            )

            # If the message has a photo/video (caption), use editMessageCaption
            # Otherwise use editMessageText — both go through styled_send
            if query.message.caption:
                await edit_caption_styled(
                    chat_id=chat_id,
                    message_id=query.message.id,
                    caption=f"{mtext}\n\n<blockquote>{reply}</blockquote>",
                    reply_markup=keyboard,
                )
            else:
                await edit_text_styled(
                    chat_id=chat_id,
                    message_id=query.message.id,
                    text=f"{mtext}\n\n<blockquote>{reply}</blockquote>",
                    reply_markup=keyboard,
                )
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════
#  ALL help callbacks handled HERE only — not in start.py
#  Order matters: most specific regex first
# ══════════════════════════════════════════════════════════════════

@app.on_callback_query(filters.regex("^help back$") & ~app.bl_users)
@lang.language()
async def _help_back(_, query: types.CallbackQuery):
    """Back → restore help_menu caption + main help buttons (no Back/Close)."""
    await edit_caption_styled(
        chat_id=query.message.chat.id,
        message_id=query.message.id,
        caption=query.lang["help_menu"],
        reply_markup=buttons.help_markup(query.lang),
    )
    await query.answer()


@app.on_callback_query(filters.regex("^help close$") & ~app.bl_users)
async def _help_close(_, query: types.CallbackQuery):
    """Close → delete the message."""
    try:
        await query.message.delete()
        await query.message.reply_to_message.delete()
    except Exception:
        pass
    await query.answer()


@app.on_callback_query(filters.regex("^help$") & ~app.bl_users)
@lang.language()
async def _help_btn(_, query: types.CallbackQuery):
    """Help button from start message → open in PM."""
    await query.answer(url=f"https://t.me/{app.username}?start=help")


@app.on_callback_query(filters.regex("^help ") & ~app.bl_users)
@lang.language()
async def _help_submenu(_, query: types.CallbackQuery):
    """Help submenu (admins, auth, blist, etc.) → show text + Back🟢 Close🔴."""
    section = query.data.split()[1]
    await edit_caption_styled(
        chat_id=query.message.chat.id,
        message_id=query.message.id,
        caption=query.lang[f"help_{section}"],
        reply_markup=buttons.help_markup(query.lang, True),
    )
    await query.answer()


# ══════════════════════════════════════════════════════════════════

@app.on_callback_query(filters.regex("settings") & ~app.bl_users)
@lang.language()
@admin_check
async def _settings_cb(_, query: types.CallbackQuery):
    cmd = query.data.split()
    if len(cmd) == 1:
        return await query.answer()
    await query.answer(query.lang["processing"], show_alert=True)

    chat_id = query.message.chat.id
    _admin = await db.get_play_mode(chat_id)
    _delete = await db.get_cmd_delete(chat_id)
    _language = await db.get_lang(chat_id)

    if cmd[1] == "delete":
        _delete = not _delete
        await db.set_cmd_delete(chat_id, _delete)
    elif cmd[1] == "play":
        await db.set_play_mode(chat_id, _admin)
        _admin = not _admin

    await query.edit_message_reply_markup(
        reply_markup=buttons.settings_markup(
            query.lang,
            _admin,
            _delete,
            _language,
            chat_id,
        )
    )


# ─── HELP COMMAND (PM only via /help command) ───
@app.on_message(filters.command(["help"]) & filters.private & ~app.bl_users)
@lang.language()
async def _help(_, message: types.Message):
    await send_styled_video(
        chat_id=message.chat.id,
        video=config.START_VDO,
        caption=message.lang["help_menu"],
        reply_markup=buttons.help_markup(message.lang),
        reply_to_message_id=message.id,
    )


# ─── START COMMAND ───
@app.on_message(filters.command(["start"]))
@lang.language()
async def start(_, message: types.Message):

    if message.from_user.id in app.bl_users and message.from_user.id not in db.notified:
        return await message.reply_text(message.lang["bl_user_notify"])

    private = message.chat.type == enums.ChatType.PRIVATE

    if len(message.command) > 1 and message.command[1] == "help":
        return await _help(_, message)

    if private:
        _text = message.lang["start_pm"].format(
            message.from_user.first_name, app.name
        )
        await send_styled_video(
            chat_id=message.chat.id,
            video=config.START_VDO,
            caption=_text,
            reply_markup=buttons.start_key(message.lang, private=True),
            reply_to_message_id=message.id,
        )
        if not await db.is_user(message.from_user.id):
            await utils.send_log(message)
            await db.add_user(message.from_user.id)

    else:
        _text = message.lang["start_gp"].format(app.name)
        key = buttons.ikm(
            [
                [buttons.ikb(text=message.lang["language"], callback_data="language")],
                [buttons.ikb(text=message.lang["channel"],  url=config.SUPPORT_CHANNEL)],
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