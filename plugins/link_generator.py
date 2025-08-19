from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from pyrogram.errors.pyromod import ListenerTimeout
from helper.helper_func import encode, get_message_id

async def ask_for_message(client, user_id, prompt_text):
    """A helper function to ask for a message and listen for the response."""
    prompt_message = await client.send_message(user_id, prompt_text, parse_mode=ParseMode.HTML)
    try:
        response = await client.listen(chat_id=user_id, filters=(filters.forwarded | (filters.text & ~filters.forwarded)), timeout=60)
        await prompt_message.delete()
        return response
    except ListenerTimeout:
        await prompt_message.edit("<b>Timeout!</b> Please try the command again.")
        return None

@Client.on_message(filters.private & filters.command('batch'))
async def batch(client: Client, message: Message):
    if message.from_user.id not in client.admins:
        return await message.reply(client.reply_text)
    
    while True:
        first_message = await ask_for_message(client, message.from_user.id, "Forward the <b>First Message</b> from the DB Channel (with quotes), or send its link.")
        if not first_message: return

        f_msg_id = await get_message_id(client, first_message)
        if f_msg_id:
            break
        else:
            await first_message.reply("❌ <b>Invalid Message</b>\n\nThis message is not from the configured DB Channel. Please try again.", quote=True)

    while True:
        second_message = await ask_for_message(client, message.from_user.id, "Now, forward the <b>Last Message</b> from the DB Channel (with quotes), or send its link.")
        if not second_message: return

        s_msg_id = await get_message_id(client, second_message)
        if s_msg_id:
            break
        else:
            await second_message.reply("❌ <b>Invalid Message</b>\n\nThis message is not from the configured DB Channel. Please try again.", quote=True)

    string = f"get-{f_msg_id * abs(client.db_channel.id)}-{s_msg_id * abs(client.db_channel.id)}"
    base64_string = await encode(string)
    link = f"https://t.me/{client.username}?start={base64_string}"
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])
    
    # --- THIS IS THE CORRECTED LINE ---
    await second_message.reply_text(
        f"<b>Generated Batch Link:</b>\n\n{link}", 
        quote=True, 
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    # --- END OF CORRECTION ---


@Client.on_message(filters.private & filters.command('genlink'))
async def link_generator(client: Client, message: Message):
    if message.from_user.id not in client.admins:
        return await message.reply(client.reply_text)
    
    while True:
        channel_message = await ask_for_message(client, message.from_user.id, "Forward a message from the DB Channel (with quotes), or send its link.")
        if not channel_message: return

        msg_id = await get_message_id(client, channel_message)
        if msg_id:
            break
        else:
            await channel_message.reply("❌ <b>Invalid Message</b>\n\nThis message is not from the configured DB Channel. Please try again.", quote=True)

    base64_string = await encode(f"get-{msg_id * abs(client.db_channel.id)}")
    link = f"https://t.me/{client.username}?start={base64_string}"
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])

    # --- THIS IS THE CORRECTED LINE ---
    await channel_message.reply_text(
        f"<b>Generated Link:</b>\n\n{link}", 
        quote=True, 
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    # --- END OF CORRECTION ---
