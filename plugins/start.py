from helper.helper_func import *
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import MessageNotModified
import humanize
import time
import asyncio
from datetime import datetime, timezone
from plugins.shortner import get_short

# --- Constants ---
CACHE_TTL_SECONDS = 300  # Cache user data for 5 minutes

# --- Main Logic Handler for File Requests ---
async def handle_file_request(client: Client, user_id: int, base64_string: str, message_or_query):
    """
    Handles a file request by enforcing the bypass timer for free users.
    Accepts either a message or a callback_query.
    """
    is_retry = isinstance(message_or_query, CallbackQuery)
    message = message_or_query.message if is_retry else message_or_query

    user_state = await get_user_state_with_cache(client, user_id)
    if user_state is None:
        error_msg = "A database error occurred. Please try again."
        return await message.edit_text(error_msg) if is_retry else await message.reply(error_msg)

    if user_id in client.admins or user_state.get('is_pro', False):
        if is_retry: await message.delete()
        await send_files_from_payload(client, message, base64_string)
        return

    # --- Free User Bypass Logic ---
    bypass_timestamp = user_state.get('bypass_ts')
    
    if not bypass_timestamp or not isinstance(bypass_timestamp, datetime):
        error_msg = "This link has expired or is invalid. Please get a new one from the source."
        if is_retry: await query.answer(error_msg, show_alert=True)
        return await message.edit_text(error_msg, reply_markup=None) if is_retry else await message.reply(error_msg)

    if bypass_timestamp.tzinfo is None:
        bypass_timestamp = bypass_timestamp.replace(tzinfo=timezone.utc)
            
    elapsed = (datetime.now(timezone.utc) - bypass_timestamp).total_seconds()

    if elapsed < client.bypass_timeout:
        remaining = int(client.bypass_timeout - elapsed)
        
        text_to_send = f"**<blockquote>🚨 ʙʏᴘᴀss ᴅᴇᴛᴇᴄᴛᴇᴅ 🚨</blockquote>\n\n<blockquote>ʜᴏᴡ ᴍᴀɴʏ ᴛɪᴍᴇs ʜᴀᴠᴇ ɪ ᴛᴏʟᴅ ʏᴏᴜ, ᴅᴏɴ'ᴛ ᴛʀʏ ᴛᴏ ᴏᴜᴛsᴍᴀʀᴛ ʏᴏᴜʀ ᴅᴀᴅ 🥸🖕\n\nɴᴏᴡ ʙᴇ ᴀ ɢᴏᴏᴅ ʙᴏʏ ᴀɴᴅ sᴏʟᴠᴇ ɪᴛ ᴀɢᴀɪɴ, ᴀɴᴅ ᴛʜɪs ᴛɪᴍᴇ ᴅᴏɴ'ᴛ ɢᴇᴛ sᴍᴀʀᴛ !! 🌚💭</blockquote>**"
        
        try:
            if is_retry:
                await message_or_query.answer("Not yet! Please wait for the timer to finish.", show_alert=True)
                if message.text != text_to_send:
                     await message.edit_text(text_to_send, reply_markup=None) # No button
            else:
                await message.reply(text_to_send, reply_markup=None) # No button
        except Exception as e:
            client.LOGGER(__name__, "RETRY_HANDLER").error(f"Error sending wait message: {e}")
        return

    await client.mongodb.increment_shortener_clicks()
    await client.mongodb.clear_bypass_timer(user_id)
    # Clear the cache to force a re-fetch of state after bypass
    if user_id in client.user_cache:
        del client.user_cache[user_id]
    
    if is_retry: await message.delete()
    await send_files_from_payload(client, message, base64_string)


# --- Pyrogram Command Handlers ---

@Client.on_message(filters.command('start') & filters.private)
@force_sub
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    
    user_state = await get_user_state_with_cache(client, user_id)
    if user_state is None: return await message.reply("A critical database error occurred. Please try again.")
    if user_state.get('banned', False): return await message.reply("**You have been banned from using this bot!**")

    # Handle simple "/start" with no payload
    if len(message.text.split()) == 1:
        buttons = [[InlineKeyboardButton("ʜᴇʟᴘ", callback_data="about"), InlineKeyboardButton("ᴄʟᴏꜱᴇ", callback_data='close')]]
        if user_id in client.admins: buttons.insert(0, [InlineKeyboardButton("⛩️ ꜱᴇᴛᴛɪɴɢꜱ ⛩️", callback_data="settings")])
        photo = client.messages.get("START_PHOTO", "")
        start_caption = client.messages.get('START', 'Welcome!').format(first=message.from_user.first_name, last=message.from_user.last_name, username=f"@{message.from_user.username}" if message.from_user.username else "N/A", mention=message.from_user.mention, id=user_id)
        try:
            if photo: await message.reply_photo(photo=photo, caption=start_caption, reply_markup=InlineKeyboardMarkup(buttons))
            else: await message.reply_text(text=start_caption, reply_markup=InlineKeyboardMarkup(buttons))
        except Exception as e: client.LOGGER(__name__, "WELCOME").error(f"Error sending welcome to {user_id}: {e}")
        return

    # Handle /start with a payload
    try:
        base64_string = message.text.split(" ", 1)[1]
        
        if base64_string.startswith("9ac1q3"):
            actual_base64 = base64_string[6:-1]
            await handle_file_request(client, user_id, actual_base64, message)
        
        else: # ORIGINAL, un-shortened link
            if user_id in client.admins or user_state.get('is_pro', False):
                await send_files_from_payload(client, message, base64_string)
                return

            await client.mongodb.set_bypass_timer(user_id)
            # Clear cache to ensure the new bypass_ts is reflected immediately on next check
            if user_id in client.user_cache:
                del client.user_cache[user_id]
            
            short_payload = f"9ac1q3{base64_string}9"
            bot_url = f"https://t.me/{client.username}?start={short_payload}"
            short_link = get_short(bot_url, client)
            
            short_photo = client.messages.get("SHORT_PIC", "")
            short_caption = client.messages.get("SHORT_MSG", "Click the button below to get your file!")
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("• ᴄʟɪᴄᴋ ʜᴇʀᴇ ᴛᴏ ᴅᴏᴡɴʟᴏᴀᴅ •", url=short_link)],[InlineKeyboardButton("ᴘʀᴇᴍɪᴜᴍ", url="https://t.me/Cultured_Oasis/5"), InlineKeyboardButton("ᴛᴜᴛᴏʀɪᴀʟ", url="https://t.me/+zYJNXKoRIGs5YmY1")]])

            if short_photo: await message.reply_photo(photo=short_photo, caption=short_caption, reply_markup=reply_markup)
            else: await message.reply(short_caption, reply_markup=reply_markup)

    except Exception as e:
        client.LOGGER(__name__, "START_CMD").error(f"Critical error in start command for {user_id}: {e}", exc_info=True)
        await message.reply("An unexpected error occurred.")


@Client.on_callback_query(filters.regex("^retry_"))
async def retry_callback_handler(client: Client, query: CallbackQuery):
    try:
        base64_string = query.data.split("_", 1)[1]
        await handle_file_request(client, query.from_user.id, base64_string, query)
    except IndexError:
        await query.message.edit_text("Invalid retry button.")


# --- Utility & Other Functions ---

async def get_user_state_with_cache(client: Client, user_id: int):
    """
    A smarter caching function that is aware of pro user expiration.
    """
    now = time.time()
    now_utc = datetime.now(timezone.utc)

    # 1. Check if user exists in cache
    if user_id in client.user_cache:
        cached_data = client.user_cache[user_id]
        
        # 2. Check if the user is a pro user according to the cache
        if cached_data.get('state', {}).get('is_pro'):
            expires_at = cached_data.get('pro_expires_at')
            # If they have an expiry date and it has passed, the cache is invalid.
            if expires_at and now_utc > expires_at:
                pass # Let the code fall through to fetch from DB
            # Otherwise, if the main cache timestamp is still fresh, return cached state
            elif (now - cached_data['timestamp']) < CACHE_TTL_SECONDS:
                return cached_data['state']
        
        # 3. For non-pro users, just check the main cache timestamp
        elif (now - cached_data['timestamp']) < CACHE_TTL_SECONDS:
            return cached_data['state']

    # 4. If cache doesn't exist, is stale, or was invalid for an expired pro, fetch from DB
    state, pro_expires_at = await client.mongodb.get_user_state(user_id)
    if state is not None:
        client.user_cache[user_id] = {
            'state': state,
            'timestamp': now,
            'pro_expires_at': pro_expires_at  # Store the expiry time for the smart check
        }
    return state


async def send_files_from_payload(client: Client, message: Message, base64_string: str):
    chat_id = message.chat.id
    try:
        string = await decode(base64_string)
        parts = string.split("-")
        
        if parts[0] != "get" or len(parts) not in [2, 3]:
            return await client.send_message(chat_id, "⚠️ **Invalid or corrupted file link.**")

        msg_id = int(int(parts[1]) / abs(client.db_channel.id))
        end_msg_id = msg_id
        if len(parts) == 3: end_msg_id = int(int(parts[2]) / abs(client.db_channel.id))
        
        message_ids = list(range(msg_id, end_msg_id + 1))
        progress_msg = await client.send_message(chat_id, "⏳ Please wait, fetching your file(s)...")
        
        file_messages = await get_messages(client, message_ids)
        await progress_msg.delete()

        if not file_messages: return await client.send_message(chat_id, "❌ **Files not found.**")
        
        sent_messages = []
        for msg in file_messages:
            try:
                sent = await msg.copy(chat_id=chat_id, protect_content=client.protect)
                sent_messages.append(sent)
                await asyncio.sleep(0.5)
            except Exception as e: client.LOGGER(__name__, "SEND").warning(f"Failed to send {getattr(msg, 'id', 'N/A')} to {chat_id}: {e}")
        
        if sent_messages and client.auto_del > 0:
            del_msg_text = f'<blockquote><i><b>his File is deleting automatically in {humanize.naturaldelta(client.auto_del)}. Forward in your Saved Messages..!</b></i></blockquote>'
            del_msg = await client.send_message(chat_id=chat_id, text=del_msg_text)
            asyncio.create_task(delete_files(sent_messages, client, del_msg, "start"))
    except Exception as e:
        client.LOGGER(__name__, "PAYLOAD").error(f"Error sending files to {chat_id}: {e}", exc_info=True)
        await client.send_message(chat_id, "An unexpected error occurred during file sending.")


# --- Other Bot Commands ---

@Client.on_message(filters.command('request') & filters.private)
async def request_command(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id in client.admins or user_id == client.owner:
        return await message.reply_text("🔹 **Admins cannot make requests.**")
    
    user_state = await get_user_state_with_cache(client, user_id)
    if user_state is None or not user_state.get('is_pro', False): 
        return await message.reply("❌ **Only premium users can make requests.**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Get Premium", url="https://t.me/Cultured_Oasis/5")]]))

    if len(message.command) < 2: return await message.reply("⚠️ **Usage:**\n`/request <content name>`")
    owner_message = f"📩 **New Request**\n\n**From:** {message.from_user.mention} (`{user_id}`)\n**Request:** `{' '.join(message.command[1:])}`"
    try:
        await client.send_message(client.owner, owner_message)
        await message.reply("✅ **Your request has been sent!**")
    except Exception as e:
        client.LOGGER(__name__, "REQUEST").error(f"Could not forward request from {user_id}: {e}")
        await message.reply("Sorry, there was an error sending your request.")

@Client.on_message(filters.command('profile') & filters.private)
async def my_plan(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id in client.admins or user_id == client.owner:
        return await message.reply_text("🔹 **You're an admin. You have access to everything!**")
    
    user_state = await get_user_state_with_cache(client, user_id)
    if user_state is None: return await message.reply("Could not fetch profile due to a database error.")
        
    if user_state.get('is_pro', False):
        # We need the raw pro_doc for the expiry date, so we fetch it directly here
        pro_data = await client.mongodb.get_pro_user(user_id)
        expires_at = pro_data.get('expires_at') if pro_data else None
        
        if expires_at and isinstance(expires_at, datetime):
            if expires_at.tzinfo is None: expires_at = expires_at.replace(tzinfo=timezone.utc)
            expiry_text = f"🔸 **Expires in:** {humanize.naturaldelta(expires_at - datetime.now(timezone.utc))}"
        else: expiry_text = "🔸 **Expiry:** Permanent"
        
        plan_text = f"**👤 Your Profile:**\n\n🔸 **Plan:** `Premium`\n{expiry_text}\n🔸 **Ads:** `Disabled`\n🔸 **Requests:** `Enabled`"
    else:
        plan_text = "**👤 Your Profile:**\n\n🔸 **Plan:** `Free`\n🔸 **Ads:** `Enabled`\n🔸 **Requests:** `Disabled`\n\n🔓 Unlock Premium to get more benefits
Contact: @MrSungChinWoo"
        
    await message.reply_text(plan_text)
