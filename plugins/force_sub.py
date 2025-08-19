from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait
from pyrogram.errors.pyromod import ListenerTimeout
from helper.helper_func import is_bot_admin

async def fsub(client, query):
    """
    Displays the Force Subscribe management menu.
    """
    # Build the channel list from the live fsub_dict for immediate updates
    channel_list_text = ""
    if client.fsub_dict:
        channel_lines = [
            f"› <i>{data[0]}</i> (<code>{channel_id}</code>)" 
            for channel_id, data in client.fsub_dict.items()
        ]
        channel_list_text = "\n".join(channel_lines)
    else:
        channel_list_text = "› <i>None configured.</i>"

    msg = f"""<blockquote><b>🔗 Force Subscribe Management</b></blockquote>
<b>Current Channels:</b>
{channel_list_text}

Use the buttons below to add or remove channels from this list.
"""
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton('➕ Add Channel', 'add_fsub'), InlineKeyboardButton('➖ Remove Channel', 'rm_fsub')],
        [InlineKeyboardButton('◂ Back to Settings', 'settings')]]
    )
    await query.message.edit_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

@Client.on_callback_query(filters.regex('^add_fsub$'))
async def add_fsub(client: Client, query: CallbackQuery):
    """
    Handles adding a new channel to the force subscribe list and updates the live dictionary.
    """
    await query.answer()
    prompt_message = await query.message.edit_text(
        """<blockquote><b>➕ Add a Force Sub Channel</b></blockquote>
Please send the channel details in this format:
<code>Channel_ID Request_Enabled Timer_in_Minutes</code>

<b>Example:</b> <code>-100123456789 yes 5</code>
› <code>-100...</code> is the Channel ID.
› <code>yes</code> enables request-to-join links. Use <code>no</code> for public invite links.
› <code>5</code> means the link will expire after 5 minutes. Use <code>0</code> for a non-expiring link.
""", parse_mode=ParseMode.HTML)
    
    try:
        response_message = await client.listen(chat_id=query.from_user.id, filters=filters.text, timeout=90)
        
        channel_info = response_message.text.split()
        if len(channel_info) != 3:
            return await response_message.reply("<b>Invalid format.</b> Please provide all three values as requested.", parse_mode=ParseMode.HTML)
        
        channel_id_str, request_str, timer_str = channel_info
        channel_id = int(channel_id_str)
        
        if any(channel[0] == channel_id for channel in client.fsub):
            return await response_message.reply("<b>This channel ID already exists in the force sub list.</b>", parse_mode=ParseMode.HTML)
        
        val, res = await is_bot_admin(client, channel_id)
        if not val:
            return await response_message.reply(f"<b>Error:</b> <code>{res}</code>", parse_mode=ParseMode.HTML)
        
        request = request_str.lower() in ('true', 'on', 'yes')
        timer = int(timer_str)

        # --- THIS IS THE FIX ---
        # 1. Update the persistent list
        client.fsub.append([channel_id, request, timer])
        
        # 2. Update the live in-memory dictionary
        chat = await client.get_chat(channel_id)
        name = chat.title
        link = None
        if timer <= 0: # Only create a permanent link if there's no timer
            try:
                # For private channels with request=False, you might need to generate a link
                if not request and chat.invite_link:
                    link = chat.invite_link
                else:
                    invite = await client.create_chat_invite_link(channel_id, creates_join_request=request)
                    link = invite.invite_link
            except Exception as e:
                client.LOGGER(__name__, client.name).warning(f"Couldn't create invite link for {channel_id}: {e}")
        
        client.fsub_dict[channel_id] = [name, link, request, timer]
        # --- END OF FIX ---
        
        # 3. Save the updated persistent list to the database
        await client.mongodb.save_settings(client.name, client.get_current_settings())
        await response_message.reply(f"✅ Channel <b>{name}</b> (<code>{channel_id}</code>) has been added successfully.", parse_mode=ParseMode.HTML)
        
    except ListenerTimeout:
        await prompt_message.edit_text("<b>Timeout! No changes were made.</b>")
    except Exception as e:
        await query.message.reply(f"<b>An error occurred:</b> <code>{e}</code>", parse_mode=ParseMode.HTML)
    
    # Refresh the menu to show the new channel immediately
    await fsub(client, query)

@Client.on_callback_query(filters.regex('^rm_fsub$'))
async def rm_fsub(client: Client, query: CallbackQuery):
    await query.answer()
    prompt_message = await query.message.edit_text(
        "<blockquote><b>➖ Remove a Force Sub Channel</b></blockquote>\nPlease send the Channel ID of the channel you want to remove.",
        parse_mode=ParseMode.HTML
    )
    try:
        response_message = await client.listen(chat_id=query.from_user.id, filters=filters.text, timeout=60)
        channel_id = int(response_message.text)
        
        # Check if the channel is in the list before trying to remove
        if not any(channel[0] == channel_id for channel in client.fsub):
            return await response_message.reply("<b>This channel ID is not in the force sub list!</b>", parse_mode=ParseMode.HTML)
        
        # Remove from the persistent list
        client.fsub = [channel for channel in client.fsub if channel[0] != channel_id]
        
        # Remove from the live dictionary
        removed_channel = client.fsub_dict.pop(channel_id, None)
        
        # Save the updated list to the database
        await client.mongodb.save_settings(client.name, client.get_current_settings())
        
        channel_name = f"<b>{removed_channel[0]}</b> " if removed_channel else ""
        await response_message.reply(f"✅ Channel {channel_name}(<code>{channel_id}</code>) has been removed.", parse_mode=ParseMode.HTML)
        
    except ListenerTimeout:
        await prompt_message.edit_text("<b>Timeout! No changes were made.</b>")
    except Exception as e:
        await query.message.reply(f"<b>An error occurred:</b> <code>{e}</code>", parse_mode=ParseMode.HTML)
        
    # Refresh the menu to show the updated list
    await fsub(client, query)
