from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from helper.helper_func import is_bot_admin

async def fsub(client, query):
    msg = f"""<blockquote>**Force Subscription Settings:**</blockquote>
**Force Subscribe Channel IDs:** `{ {a[0] for a in client.fsub} if client.fsub else "None"}`

__Use the appropriate button below to add or remove a force subscription channel based on your needs!__
"""
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton('ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ', 'add_fsub'), InlineKeyboardButton('ʀᴇᴍᴏᴠᴇ ᴄʜᴀɴɴᴇʟ', 'rm_fsub')],
        [InlineKeyboardButton('◂ ʙᴀᴄᴋ', 'settings')]]
    )
    await query.message.edit_text(msg, reply_markup=reply_markup)
    return

@Client.on_callback_query(filters.regex('^add_fsub$'))
async def add_fsub(client: Client, query: CallbackQuery):
    await query.answer()
    try:
        ask_channel_info = await client.ask(query.from_user.id, "Send channel id (negative integer value), request boolean (yes/no), and timer in minutes (integer, 0 for no timer), separated by spaces.\n\n**Example:** `-10089479289 yes 5`\n\nThis means channel `-10089479289` will use request-to-join links that expire in 5 minutes.", filters=filters.text, timeout=60)
        
        channel_info = ask_channel_info.text.split()
        if len(channel_info) != 3:
            return await ask_channel_info.reply("**Invalid format. Please provide all three values.**")
        
        channel_id, request_str, timer_str = channel_info
        channel_id = int(channel_id)
        
        if any(channel[0] == channel_id for channel in client.fsub):
            return await ask_channel_info.reply("**This channel ID already exists in the force sub list.**")
        
        val, res = await is_bot_admin(client, channel_id)
        if not val:
            return await ask_channel_info.reply(f"**Error:** `{res}`")
        
        if request_str.lower() in ('true', 'on', 'yes'):
            request = True
        elif request_str.lower() in ('false', 'off', 'no'):
            request = False
        else:
            raise ValueError("Invalid request value. Use 'yes' or 'no'.")
        
        timer = int(timer_str)

        client.fsub.append([channel_id, request, timer])
        
        chat = await client.get_chat(channel_id)
        name = chat.title
        
        # Save settings to database
        await client.mongodb.save_settings(client.name, client.get_current_settings())
        
        await fsub(client, query)
        await ask_channel_info.reply(f"✅ Channel **{name}** has been added to the force sub list.")
    except Exception as e:
        await query.message.reply(f"**An error occurred:** `{e}`")

@Client.on_callback_query(filters.regex('^rm_fsub$'))
async def rm_fsub(client: Client, query: CallbackQuery):
    await query.answer()
    try:
        ask_channel_info = await client.ask(query.from_user.id, "Send the channel ID (negative integer value) to remove.", filters=filters.text, timeout=60)
        
        channel_id = int(ask_channel_info.text)
        
        if not any(channel[0] == channel_id for channel in client.fsub):
            return await ask_channel_info.reply("**This channel ID is not in the force sub list!**")
        
        client.fsub = [channel for channel in client.fsub if channel[0] != channel_id]
        
        # Save settings to database
        await client.mongodb.save_settings(client.name, client.get_current_settings())
        
        await fsub(client, query)
        await ask_channel_info.reply(f"✅ Channel with ID `{channel_id}` has been removed from the force sub list.")
    except Exception as e:
        await query.message.reply(f"**An error occurred:** `{e}`")
