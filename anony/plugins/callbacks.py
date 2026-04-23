# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

import re

from pyrogram import errors, filters, types

from anony import anon, app, db, lang, queue, tg, yt
from anony.helpers import admin_check, buttons, can_manage_vc
from anony.helpers.styled_send import edit_styled, edit_caption_styled, edit_text_styled


@app.on_callback_query(filters.regex("cancel_dl") & ~app.bl_users)
@lang.language()
async def cancel_dl(_, query: types.CallbackQuery):
    await query.answer()
    await tg.cancel(query)


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
            await query.message.reply_text(reply, quote=False)
            await query.message.delete()
        else:
            mtext = re.sub(
                r"\n\n<blockquote>.*?</blockquote>",
                "",
                query.message.caption.html if query.message.photo else query.message.text.html,
                flags=re.DOTALL,
            )
            keyboard = buttons.controls(
                chat_id, status=status if action != "resume" else None
            )
            new_text = f"{mtext}\n\n<blockquote>{reply}</blockquote>"

            # Use caption variant for photo messages, text variant for plain text.
            # Both go through HTTP Bot API so style= colours are preserved.
            if query.message.photo:
                await edit_caption_styled(
                    chat_id=chat_id,
                    message_id=query.message.id,
                    caption=new_text,
                    reply_markup=keyboard,
                )
            else:
                await edit_text_styled(
                    chat_id=chat_id,
                    message_id=query.message.id,
                    text=new_text,
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
        reply_markup=buttons.help_markup(query.lang),   # main grid, no back/close
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
    section = query.data.split()[1]   # e.g. "admins"
    await edit_caption_styled(
        chat_id=query.message.chat.id,
        message_id=query.message.id,
        caption=query.lang[f"help_{section}"],
        reply_markup=buttons.help_markup(query.lang, True),  # back=True → Back+Close
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