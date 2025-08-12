from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

@Client.on_callback_query(filters.regex("^admins$"))
async def admins(client: Client, query: CallbackQuery):
    if not (query.from_user.id == client.owner):
        return await query.answer('This can only be used by the owner.', show_alert=True)
    
    admin_list = ", ".join(f"`{a}`" for a in client.admins if a != client.owner)
    msg = f"""<blockquote>**Admin Settings:**</blockquote>
**Owner ID:** `{client.owner}`
**Admin User IDs:** {admin_list or "None"}

__Use the buttons below to add or remove admins.__
"""
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton('ᴀᴅᴅ ᴀᴅᴍɪɴ', 'add_admin'), InlineKeyboardButton('ʀᴇᴍᴏᴠᴇ ᴀᴅᴍɪɴ', 'rm_admin')],
        [InlineKeyboardButton('◂ ʙᴀᴄᴋ', 'settings')]
    ])
    await query.message.edit_text(msg, reply_markup=reply_markup)

@Client.on_callback_query(filters.regex("^add_admin$"))
async def add_new_admins(client: Client, query: CallbackQuery):
    await query.answer()
    try:
        ids_msg = await client.ask(query.from_user.id, "Send user IDs to add, separated by a space.", filters=filters.text, timeout=60)
        ids = ids_msg.text.split()
        added_count = 0
        for i in ids:
            if i.isdigit():
                user_id = int(i)
                if user_id not in client.admins:
                    client.admins.append(user_id)
                    added_count += 1
        if added_count > 0:
            await client.mongodb.save_settings(client.session_name, client.get_current_settings())
            await ids_msg.reply(f"✅ Added {added_count} new admin(s).")
        else:
            await ids_msg.reply("No new admins were added.")
    except Exception as e:
        await query.message.reply(f"An error occurred: {e}")
    
    await admins(client, query)

@Client.on_callback_query(filters.regex("^rm_admin$"))
async def remove_admins(client: Client, query: CallbackQuery):
    await query.answer()
    try:
        ids_msg = await client.ask(query.from_user.id, "Send user IDs to remove, separated by a space.", filters=filters.text, timeout=60)
        ids = ids_msg.text.split()
        removed_count = 0
        for i in ids:
            if i.isdigit():
                user_id = int(i)
                if user_id == client.owner:
                    await ids_msg.reply("You cannot remove the owner.")
                    continue
                if user_id in client.admins:
                    client.admins.remove(user_id)
                    removed_count += 1
        if removed_count > 0:
            await client.mongodb.save_settings(client.session_name, client.get_current_settings())
            await ids_msg.reply(f"🗑️ Removed {removed_count} admin(s).")
        else:
            await ids_msg.reply("No admins were removed.")
    except Exception as e:
        await query.message.reply(f"An error occurred: {e}")

    await admins(client, query)
