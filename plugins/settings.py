import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors.pyromod import ListenerTimeout
from pyrogram.errors import FloodWait

#===============================================================#
# Main Settings Panel
#===============================================================#
@Client.on_callback_query(filters.regex("^settings$"))
async def settings_panel(client, query):
    # This function now reloads data directly before displaying
    # to ensure it's always up-to-date.
    saved_settings = await client.mongodb.load_settings(client.session_name)
    if saved_settings:
        client.protect = saved_settings.get("protect", False)
        client.auto_del = saved_settings.get("auto_del", 0)
        client.disable_btn = saved_settings.get("disable_btn", False)
        client.admins = saved_settings.get("admins", [client.owner])
        client.fsub = saved_settings.get("fsub", [])
        client.short_url = saved_settings.get("short_url", "")
        client.short_api = saved_settings.get("short_api", "")

    # --- Fetching FSub Channel Details ---
    fsub_channels_text = []
    if client.fsub:
        for ch_id, req_mode, timer in client.fsub:
            try:
                # Use client.get_chat to fetch channel name
                chat = await client.get_chat(ch_id)
                channel_name = chat.title
                fsub_channels_text.append(f"│  › {channel_name} (<code>{ch_id}</code>)")
            except FloodWait as e:
                await asyncio.sleep(e.x)
                chat = await client.get_chat(ch_id)
                fsub_channels_text.append(f"│  › {chat.title} (<code>{ch_id}</code>)")
            except Exception:
                # Handle cases where the bot might not be in the channel anymore
                fsub_channels_text.append(f"│  › <i>Invalid or Inaccessible Channel</i> (<code>{ch_id}</code>)")
    
    fsub_details = "\n".join(fsub_channels_text) if fsub_channels_text else "│  › No channels configured."


    # --- Aesthetic Display ---
    status_protect = "Enabled" if client.protect else "Disabled"
    status_share_button = "Enabled" if not client.disable_btn else "Disabled"
    auto_del_status = f"{client.auto_del}s" if client.auto_del > 0 else "Disabled"
    shortener_status = "Enabled" if client.short_url and client.short_api else "Disabled"
    
    msg = f"""<blockquote>
╭─ • 「 <b>Settings Overview</b> 」
│
├─ <b>Content & Access</b>
│  › 🛡️ Protect: <code>{status_protect}</code>
│  › 🔄 Share Button: <code>{status_share_button}</code>
│  › ⏰ Auto-Delete: <code>{auto_del_status}</code>
│
├─ <b>Users & Monetization</b>
│  › 👑 Admins: <code>{len(client.admins)}</code>
│  › 💰 Shortener: <code>{shortener_status}</code>
│
╰─ • @{client.username}</blockquote>
<blockquote>
╭─ • 「 <b>Force Subscribe Channels</b> 」
│
{fsub_details}
│
╰─ • </blockquote>"""

    # --- Clean & Simple Keyboard ---
    reply_markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton('🛡️ Protect', callback_data='protect'),
                InlineKeyboardButton('⏰ Auto-Delete', callback_data='auto_del'),
                InlineKeyboardButton('🔄 Share Btn', callback_data='disable_btn_toggle'),
            ],
            [
                InlineKeyboardButton('👑 Admins', callback_data='admins'),
                InlineKeyboardButton('🔗 Force Sub', callback_data='fsub')
            ],
            [
                InlineKeyboardButton('📝 Texts', callback_data='texts'),
                InlineKeyboardButton('🖼️ Photos', callback_data='photos')
            ],
            [
                InlineKeyboardButton('💰 Shortener', callback_data='shortner_settings')
            ],
            [
                InlineKeyboardButton('« Back to Home', callback_data='home')
            ]
        ]
    )
    
    await query.message.edit_text(msg, reply_markup=reply_markup)


#===============================================================#
# Handlers for Direct Toggles (that stay in this file)
#===============================================================#

@Client.on_callback_query(filters.regex("^protect$"))
async def protect_callback(client, query):
    client.protect = not client.protect
    await client.mongodb.save_settings(client.session_name, client.get_current_settings())
    await query.answer(f"Protect Content is now {'Enabled' if client.protect else 'Disabled'}", show_alert=True)
    await settings_panel(client, query)

@Client.on_callback_query(filters.regex("^disable_btn_toggle$"))
async def disable_btn_callback(client, query):
    client.disable_btn = not client.disable_btn
    await client.mongodb.save_settings(client.session_name, client.get_current_settings())
    # Note the inverted logic: `disable_btn=True` means the button is *disabled*.
    await query.answer(f"Share Button is now {'Disabled' if client.disable_btn else 'Enabled'}", show_alert=True)
    await settings_panel(client, query)

@Client.on_callback_query(filters.regex("^auto_del$"))
async def auto_del_callback(client, query):
    await query.answer()
    try:
        current_timer_display = f"{client.auto_del} seconds" if client.auto_del > 0 else "Disabled"
        ask_msg = await client.ask(
            chat_id=query.from_user.id,
            text=f"Current auto-delete timer is `{current_timer_display}`.\n\nEnter a new time in seconds (use 0 to disable).",
            filters=filters.text, timeout=60
        )
        if ask_msg.text.isdigit():
            client.auto_del = int(ask_msg.text)
            await client.mongodb.save_settings(client.session_name, client.get_current_settings())
            new_timer_display = f"{client.auto_del} seconds" if client.auto_del > 0 else "Disabled"
            await ask_msg.reply(f"✅ Auto-delete timer updated to `{new_timer_display}`.")
        else:
            await ask_msg.reply("❌ Invalid input. Please enter a valid number.")
    except ListenerTimeout:
        await query.message.reply("⏰ Timeout. Operation cancelled.")
    
    await settings_panel(client, query)
