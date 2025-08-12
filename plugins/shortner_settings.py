from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors.pyromod import ListenerTimeout

# Import the main settings panel to navigate back
from .settings import settings_panel

# This function displays the shortener sub-menu
async def shortner_settings_main(client: Client, query: CallbackQuery):
    await query.answer()
    api_key_display = f"{'*' * (len(client.short_api) - 4)}{client.short_api[-4:]}" if client.short_api and len(client.short_api) > 4 else "Not Set"
    
    msg = f"""<blockquote>**Shortener Settings:**</blockquote>
**Current URL:** `{client.short_url or "Not Set"}`
**Current API Key:** `{api_key_display}`

__Manage your URL shortener configuration. Changes are saved instantly.__
"""
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton('ᴄʜᴀɴɢᴇ ᴜʀʟ', 'change_short_url'), InlineKeyboardButton('ᴄʜᴀɴɢᴇ ᴀᴘɪ', 'change_short_api')],
        [InlineKeyboardButton('◂ ʙᴀᴄᴋ', 'settings')]
    ])
    await query.message.edit_text(msg, reply_markup=reply_markup)

# This handler is triggered when the "ꜱʜᴏʀᴛɴᴇʀ" button is clicked in the main settings
@Client.on_callback_query(filters.regex("^shortner_settings$"))
async def shortner_settings_callback(client: Client, query: CallbackQuery):
    if not (query.from_user.id == client.owner):
        return await query.answer('This can only be used by the owner.', show_alert=True)
    await shortner_settings_main(client, query)

# This handler changes the URL
@Client.on_callback_query(filters.regex("^change_short_url$"))
async def change_short_url(client: Client, query: CallbackQuery):
    await query.answer()
    try:
        ask_msg = await client.ask(
            chat_id=query.from_user.id,
            text="Please send the new shortener URL (e.g., `your.domain.com`).\n\nType `cancel` to abort.",
            filters=filters.text, timeout=60
        )
        if ask_msg.text.lower() == 'cancel':
            await ask_msg.reply("Operation cancelled.")
        else:
            client.short_url = ask_msg.text.strip()
            # Save the new setting to the database
            await client.mongodb.save_settings(client.session_name, client.get_current_settings())
            await ask_msg.reply(f"✅ Shortener URL updated to: `{client.short_url}`")
    except ListenerTimeout:
        await query.message.reply("⏰ Timeout! Operation cancelled.")
    
    # Refresh the shortener settings menu
    await shortner_settings_main(client, query)

# This handler changes the API key
@Client.on_callback_query(filters.regex("^change_short_api$"))
async def change_short_api(client: Client, query: CallbackQuery):
    await query.answer()
    try:
        ask_msg = await client.ask(
            chat_id=query.from_user.id,
            text="Please send the new shortener API key.\n\nType `cancel` to abort.",
            filters=filters.text, timeout=60
        )
        if ask_msg.text.lower() == 'cancel':
            await ask_msg.reply("Operation cancelled.")
        else:
            client.short_api = ask_msg.text.strip()
            # Save the new setting to the database
            await client.mongodb.save_settings(client.session_name, client.get_current_settings())
            await ask_msg.reply("✅ Shortener API key updated successfully.")
    except ListenerTimeout:
        await query.message.reply("⏰ Timeout! Operation cancelled.")

    # Refresh the shortener settings menu
    await shortner_settings_main(client, query)
