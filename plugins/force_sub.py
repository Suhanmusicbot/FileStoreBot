from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from helper.helper_func import is_bot_admin

@Client.on_callback_query(filters.regex("^fsub$"))
async def fsub(client: Client, query: CallbackQuery):
    channel_list = "\n".join([f"• `{ch[0]}` (Request: {ch[1]}, Timer: {ch[2]}m)" for ch in client.fsub])
    msg = f"""<blockquote>**Force Subscription Settings:**</blockquote>
{channel_list or "No channels configured."}

__Manage the channels users must join to use the bot.__
"""
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton('ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ', 'add_fsub'), InlineKeyboardButton('ʀᴇᴍᴏᴠᴇ ᴄʜᴀɴɴᴇʟ', 'rm_fsub')],
        [InlineKeyboardButton('◂ ʙᴀᴄᴋ', 'settings')]
    ])
    await query.message.edit_text(msg, reply_markup=reply_markup)

@Client.on_callback_query(filters.regex('^add_fsub$'))
async def add_fsub_channel(client: Client, query: CallbackQuery):
    await query.answer()
    try:
        ask_msg = await client.ask(
            query.from_user.id,
            "Send channel details in this format:\n`channel_id request_mode timer_in_minutes`\n\n**Example:** `-10012345 true 5`\n(request_mode can be `true` or `false`)",
            filters=filters.text, timeout=120
        )
        parts = ask_msg.text.split()
        if len(parts) != 3:
            return await ask_msg.reply("❌ Invalid format. Please try again.")

        channel_id = int(parts[0])
        request_mode = parts[1].lower() == 'true'
        timer = int(parts[2])

        if any(ch[0] == channel_id for ch in client.fsub):
            return await ask_msg.reply("This channel is already in the list.")

        is_admin, error_msg = await is_bot_admin(client, channel_id)
        if not is_admin:
            return await ask_msg.reply(f"Error: {error_msg}")

        client.fsub.append([channel_id, request_mode, timer])
        await client.mongodb.save_settings(client.session_name, client.get_current_settings())
        await ask_msg.reply("✅ Channel added successfully.")
    except Exception as e:
        await query.message.reply(f"An error occurred: {e}")
    
    await fsub(client, query)

@Client.on_callback_query(filters.regex('^rm_fsub$'))
async def rm_fsub_channel(client: Client, query: CallbackQuery):
    await query.answer()
    try:
        ask_msg = await client.ask(query.from_user.id, "Send the Channel ID to remove.", filters=filters.text, timeout=60)
        channel_id_to_remove = int(ask_msg.text)
        
        initial_len = len(client.fsub)
        client.fsub = [ch for ch in client.fsub if ch[0] != channel_id_to_remove]
        
        if len(client.fsub) < initial_len:
            await client.mongodb.save_settings(client.session_name, client.get_current_settings())
            await ask_msg.reply("🗑️ Channel removed successfully.")
        else:
            await ask_msg.reply("Channel not found in the list.")
    except Exception as e:
        await query.message.reply(f"An error occurred: {e}")
        
    await fsub(client, query)
