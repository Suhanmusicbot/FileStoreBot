from helper.helper_func import *
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode  # <--- IMPORT THIS
import humanize
from config import MSG_EFFECT
import asyncio
from datetime import timedelta

@Client.on_message(filters.command('start') & filters.private)
@force_sub
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    present = await client.mongodb.present_user(user_id)
    if not present:
        try:
            await client.mongodb.add_user(user_id)
        except Exception as e:
            client.LOGGER(__name__, client.name).warning(f"Error adding a user:\n{e}")
    is_banned = await client.mongodb.is_banned(user_id)
    if is_banned:
        return await message.reply("**You have been banned from using this bot!**")
    
    text = message.text
    if len(text) > 7:
        try:
            base64_string = text.split(" ", 1)[1]
        except IndexError:
            return

        string = await decode(base64_string)
        argument = string.split("-")
        
        ids = []
        if len(argument) == 3:
            try:
                start = int(int(argument[1]) / abs(client.db))
                end = int(int(argument[2]) / abs(client.db))
                ids = range(start, end + 1) if start <= end else list(range(start, end - 1, -1))
            except Exception as e:
                client.LOGGER(__name__, client.name).warning(f"Error decoding IDs: {e}")
                return

        elif len(argument) == 2:
            try:
                if hasattr(client, 'db_channel') and client.db_channel:
                    ids = [int(int(argument[1]) / abs(client.db_channel.id))]
                else:
                    await message.reply("Database channel is not configured correctly.")
                    return
            except Exception as e:
                client.LOGGER(__name__, client.name).warning(f"Error decoding ID: {e}")
                return
        
        temp_msg = await message.reply("Please wait, fetching your files...")
        
        messages = []
        try:
            messages = await get_messages(client, ids)
        except Exception as e:
            await temp_msg.edit_text("Something went wrong while fetching files.")
            client.LOGGER(__name__, client.name).warning(f"Error getting messages: {e}")
            return
        
        if not messages:
            await temp_msg.edit("Couldn't find the files in the database.")
            return
        
        await temp_msg.delete()

        yugen_msgs = []

        for msg in messages:
            caption = msg.caption.html if msg.caption else ""
            reply_markup = msg.reply_markup if not client.disable_btn else None

            try:
                copied_msg = await msg.copy(
                    chat_id=message.from_user.id, 
                    caption=caption, 
                    reply_markup=reply_markup, 
                    protect_content=client.protect,
                    parse_mode=ParseMode.HTML  # <--- ADD THIS
                )
                yugen_msgs.append(copied_msg)
            except FloodWait as e:
                await asyncio.sleep(e.x)
                copied_msg = await msg.copy(
                    chat_id=message.from_user.id, 
                    caption=caption, 
                    reply_markup=reply_markup, 
                    protect_content=client.protect,
                    parse_mode=ParseMode.HTML  # <--- AND ADD THIS
                )
                yugen_msgs.append(copied_msg)
            except Exception as e:
                client.LOGGER(__name__, client.name).warning(f"Failed to send message: {e}")
        
        if yugen_msgs and client.auto_del > 0:
            enter = text
            k = await client.send_message(
                chat_id=message.from_user.id, 
                text=f'<blockquote><b><i>These files will be deleted in {humanize.naturaldelta(timedelta(seconds=client.auto_del))}. Please save them.</i></b></blockquote>',
                parse_mode=ParseMode.HTML  # <--- AND ADD THIS
            )
            asyncio.create_task(delete_files(yugen_msgs, client, k, enter))
    else:
        buttons = [[InlineKeyboardButton("ʜᴇʟᴘ", callback_data = "about"), InlineKeyboardButton("ᴄʟᴏꜱᴇ", callback_data = "close")]]
        if user_id in client.admins:
            buttons.insert(0, [InlineKeyboardButton("⛩️ ꜱᴇᴛᴛɪɴɢꜱ ⛩️", callback_data="settings")])
        
        photo = client.messages.get("START_PHOTO", "")
        
        start_text = client.messages.get('START', 'No Start Message').format(
            first=message.from_user.first_name,
            last=message.from_user.last_name,
            username=None if not message.from_user.username else '@' + message.from_user.username,
            mention=message.from_user.mention,
            id=message.from_user.id
        )

        if photo:
            await client.send_photo(
                chat_id=message.chat.id,
                photo=photo,
                caption=start_text,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.HTML  # <--- ADD THIS
            )
        else:
            await client.send_message(
                chat_id=message.chat.id,
                text=start_text,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.HTML  # <--- AND ADD THIS
            )
