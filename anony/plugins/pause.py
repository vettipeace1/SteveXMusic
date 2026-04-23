from pyrogram import filters, types

from anony import anon, app, db, lang, queue
from anony.helpers import buttons, can_manage_vc
from anony.helpers.styled_send import edit_text_styled, edit_caption_styled


@app.on_message(filters.command(["pause"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _pause(_, m: types.Message):
    if not await db.get_call(m.chat.id):
        return await m.reply_text(m.lang["not_playing"])

    if not await db.playing(m.chat.id):
        return await m.reply_text(m.lang["play_already_paused"])

    await anon.pause(m.chat.id)

    media = queue.get_current(m.chat.id)
    if not media or not media.message_id:
        return

    text = m.lang["play_paused"].format(m.from_user.mention)
    keyboard = buttons.controls(m.chat.id, status=m.lang["paused"])

    try:
        if media.video:
            await edit_caption_styled(
                chat_id=m.chat.id,
                message_id=media.message_id,
                caption=f"{media.caption}\n\n<blockquote>{text}</blockquote>",
                reply_markup=keyboard,
            )
        else:
            await edit_text_styled(
                chat_id=m.chat.id,
                message_id=media.message_id,
                text=f"{media.caption}\n\n<blockquote>{text}</blockquote>",
                reply_markup=keyboard,
            )
    except Exception:
        pass