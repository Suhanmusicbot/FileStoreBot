from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
from pyrogram.errors.pyromod import ListenerTimeout
from config import OWNER_ID
import humanize

@Client.on_callback_query(filters.regex("^settings$"))
async def settings(client, query):
    """
    Displays the main settings menu, now showing a list of configured Force Sub channels.
    """
    # --- New logic to build the list of Force Subscribe channels ---
    fsub_channels_text = ""
    if client.fsub_dict:
        # Create a formatted line for each channel
        channel_lines = [
            f"› <i>{data[0]}</i> (<code>{channel_id}</code>)" 
            for channel_id, data in client.fsub_dict.items()
        ]
        fsub_channels_text = "\n".join(channel_lines)
    else:
        fsub_channels_text = "› <i>None configured.</i>"
    # --- End of new logic ---

    protect_status_text = f"Content Protection: {'✅ Enabled' if client.protect else '❌ Disabled'}"
    
    # Updated message text to include the channel list
    msg = f"""<blockquote><b>⚙️ Bot Settings</b></blockquote>

<b><u>Force Subscribe Channels:</u></b>
{fsub_channels_text}

<b><u>Core Configuration:</u></b>
› <b>Admins:</b> <code>{len(client.admins)} users</code>
› <b>Auto Delete:</b> <code>{f"{client.auto_del} seconds" if client.auto_del > 0 else "Disabled"}</code>
"""

    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Admins", callback_data="admins"), InlineKeyboardButton("🔗 Manage Channels", callback_data="fsub")],
        [InlineKeyboardButton(protect_status_text, callback_data="protect")],
        [InlineKeyboardButton("⏱️ Set Auto Delete Timer", callback_data="auto_del")],
        [InlineKeyboardButton("🎨 Customize Appearance", callback_data="customize")],
        [InlineKeyboardButton("🏠 Back to Home", callback_data="home")]
    ])
    
    await query.message.edit_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

@Client.on_callback_query(filters.regex("^customize$"))
async def customize(client, query):
    """
    Shows the menu for customizing the bot's text and media.
    """
    msg = """<blockquote><b>🎨 Customize Appearance</b></blockquote>

Use the buttons below to change the bot's messages, welcome photos, and more.
"""
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Message Texts", callback_data="texts")],
        [InlineKeyboardButton("🖼️ Media & Photos", callback_data="photos")],
        [InlineKeyboardButton("◂ Back to Settings", callback_data="settings")]
    ])
    await query.message.edit_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


@Client.on_callback_query(filters.regex("^fsub$"))
async def fsub_settings_cb(client, query):
    from plugins.force_sub import fsub
    await fsub(client, query)

@Client.on_callback_query(filters.regex("^admins$"))
async def admins_settings_cb(client, query):
    from plugins.admins import admins
    await admins(client, query)

@Client.on_callback_query(filters.regex("^photos$"))
async def photos(client, query):
    msg = f"""<blockquote><b>🖼️ Media & Photos</b></blockquote>
Set or remove the images used in the bot's messages.

› <b>Start Photo:</b> <code>{'Set' if client.messages.get('START_PHOTO') else 'Not Set'}</code>
› <b>FSUB Photo:</b> <code>{'Set' if client.messages.get('FSUB_PHOTO') else 'Not Set'}</code>
"""
    reply_markup = InlineKeyboardMarkup([
    [
        InlineKeyboardButton(
            ('SET' if not client.messages.get("START_PHOTO") else 'CHANGE') + ' START PHOTO', 
            callback_data='add_start_photo'
        ),
        InlineKeyboardButton(
            ('SET' if not client.messages.get("FSUB_PHOTO") else 'CHANGE') + ' FSUB PHOTO', 
            callback_data='add_fsub_photo'
        )
    ],
    [
        InlineKeyboardButton('🗑️ REMOVE START PHOTO', callback_data='rm_start_photo'),
        InlineKeyboardButton('🗑️ REMOVE FSUB PHOTO', callback_data='rm_fsub_photo')
    ],
    [InlineKeyboardButton('◂ Back', callback_data='customize')]
    ])
    await query.message.edit_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

@Client.on_callback_query(filters.regex("^protect$"))
async def protect(client, query):
    client.protect = not client.protect
    await client.mongodb.save_settings(client.name, client.get_current_settings())
    await query.answer(f"Content Protection has been {'Enabled' if client.protect else 'Disabled'}")
    await settings(client, query) # Refresh the settings menu

@Client.on_callback_query(filters.regex("^auto_del$"))
async def auto_del(client, query):
    await query.answer()
    try:
        await query.message.edit_text(
            f"<blockquote><b>⏱️ Set Auto Delete Timer</b></blockquote>\n<b>Current Timer:</b> <code>{client.auto_del} seconds</code>\n\nEnter a new time in seconds. Use <code>0</code> to disable.",
            parse_mode=ParseMode.HTML
        )
        res = await client.listen(query.from_user.id, filters=filters.text, timeout=60)
        
        timer = int(res.text.strip())
        if timer >= 0:
            client.auto_del = timer
            await client.mongodb.save_settings(client.name, client.get_current_settings())
            await res.reply_text(f'✅ Auto Delete timer has been set to <b>{timer} seconds</b>!', parse_mode=ParseMode.HTML)
        else:
            await res.reply_text("❌ Invalid input. Please enter a non-negative number.", parse_mode=ParseMode.HTML)
    except ListenerTimeout:
        await query.message.reply_text("<b>Timeout! No changes were made.</b>", parse_mode=ParseMode.HTML)
    except ValueError:
        await query.message.reply_text("<b>❌ Invalid input. Please enter a valid number.</b>", parse_mode=ParseMode.HTML)
    
    await settings(client, query) # Go back to settings menu after action


@Client.on_callback_query(filters.regex("^texts$"))
async def texts_settings_cb(client, query):
    from plugins.texts import texts
    await texts(client, query)

@Client.on_callback_query(filters.regex('^rm_start_photo$'))
async def rm_start_photo(client, query):
    client.messages['START_PHOTO'] = ''
    await client.mongodb.save_settings(client.name, client.get_current_settings())
    await query.answer("Start Photo Removed!", show_alert=True)
    await photos(client, query)

@Client.on_callback_query(filters.regex('^rm_fsub_photo$'))
async def rm_fsub_photo(client, query):
    client.messages['FSUB_PHOTO'] = ''
    await client.mongodb.save_settings(client.name, client.get_current_settings())
    await query.answer("FSUB Photo Removed!", show_alert=True)
    await photos(client, query)

async def handle_photo_update(client, query, photo_key, prompt_text):
    await query.answer()
    try:
        await query.message.edit_text(prompt_text, parse_mode=ParseMode.HTML)
        res = await client.listen(query.from_user.id, filters=(filters.text | filters.photo), timeout=60)
        
        photo_val = ""
        if res.photo:
            photo_val = res.photo.file_id
        elif res.text and (res.text.startswith('https://') or res.text.startswith('http://')):
            photo_val = res.text
        
        if photo_val:
            client.messages[photo_key] = photo_val
            await client.mongodb.save_settings(client.name, client.get_current_settings())
            await query.message.edit_text(f"✅ <b>{photo_key.replace('_', ' ').title()}</b> has been updated!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('◂ Back', 'photos')]]), parse_mode=ParseMode.HTML)
        else:
            await query.message.edit_text("❌ Invalid input. Please send a photo or a valid URL.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('◂ Back', 'photos')]]), parse_mode=ParseMode.HTML)
    except ListenerTimeout:
        await query.message.edit_text("<b>Timeout! No changes were made.</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('◂ Back', 'photos')]]), parse_mode=ParseMode.HTML)

@Client.on_callback_query(filters.regex("^add_start_photo$"))
async def add_start_photo(client, query):
    await handle_photo_update(client, query, 'START_PHOTO', "<blockquote>Please send the photo for the <b>Start Message</b>.</blockquote>")

@Client.on_callback_query(filters.regex("^add_fsub_photo$"))
async def add_fsub_photo(client, query):
    await handle_photo_update(client, query, 'FSUB_PHOTO', "<blockquote>Please send the photo for the <b>Force Subscribe Message</b>.</blockquote>")
