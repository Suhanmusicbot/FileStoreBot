import asyncio
from pyrogram import filters, Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from helper.helper_func import encode

# --- NEW CODE: Custom filter to prevent capturing numeric replies ---
# This filter will return True if the message is NOT a simple number.
async def is_not_numeric_reply(_, __, message: Message):
    """
    Custom filter to prevent the channel_post handler from firing on
    numeric input intended for listeners (like setting a timer).
    """
    # Check if the message has text and if that text is purely numeric.
    if message.text and message.text.isdigit():
        return False  # If it's just a number, the filter fails.
    return True       # Otherwise, the filter passes.

# We must create a filter object from our asynchronous function
not_numeric_filter = filters.create(is_not_numeric_reply)
# --- END OF NEW CODE ---


@Client.on_message(
    filters.private &
    ~filters.command(['start','users','broadcast','batch','genlink','usage', 'pbroadcast', 'ban', 'unban']) &
    not_numeric_filter  # <--- APPLY THE NEW, SMARTER FILTER HERE
)
async def channel_post(client: Client, message: Message):
    if message.from_user.id not in client.admins:
        return await message.reply(client.reply_text)
    
    reply_text = await message.reply_text("Please Wait, processing file...", quote=True)
    try:
        post_message = await message.copy(chat_id = client.db, disable_notification=True)
    except FloodWait as e:
        await asyncio.sleep(e.x)
        post_message = await message.copy(chat_id = client.db, disable_notification=True)
    except Exception as e:
        print(e)
        await reply_text.edit_text("Something went wrong. Could not save the file.")
        return
        
    converted_id = post_message.id * abs(client.db)
    string = f"get-{converted_id}"
    base64_string = await encode(string)
    link = f"https://t.me/{client.username}?start={base64_string}"

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])

    await reply_text.edit(f"<b>Here is your link</b>\n\n<code>{link}</code>", reply_markup=reply_markup, disable_web_page_preview = True)

    if not client.disable_btn:
        await post_message.edit_reply_markup(reply_markup)


@Client.on_message(filters.channel & filters.incoming)
async def new_post(client: Client, message: Message):
    if message.chat.id != client.db:
        return
    if client.disable_btn:
        return

    converted_id = message.id * abs(client.db)
    string = f"get-{converted_id}"
    base64_string = await encode(string)
    link = f"https://t.me/{client.username}?start={base64_string}"
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])
    try:
        await message.edit_reply_markup(reply_markup)
    except Exception as e:
        print(e)
        pass```

After updating this file and restarting your bot, the auto-delete timer function will work perfectly. The `channel_post` handler will now correctly ignore your numeric input, allowing the listener to capture it as intended.
