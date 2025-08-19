from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors.pyromod import ListenerTimeout

async def texts(client, query):
    msg = f"""<blockquote>**Text Configuration:**</blockquote>
**Start Message:**
<pre>{client.messages.get('START', 'Empty')}</pre>
**Force Sub Message:**
<pre>{client.messages.get('FSUB', 'Empty')}</pre>
**About Message:**
<pre>{client.messages.get('ABOUT', 'Empty')}</pre>
**Reply Message:**
<pre>{client.reply_text}</pre>
    """
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(f'ꜱᴛᴀʀᴛ ᴛᴇxᴛ', 'start_txt'), InlineKeyboardButton(f'ꜰꜱᴜʙ ᴛᴇxᴛ', 'fsub_txt')],
        [InlineKeyboardButton('ʀᴇᴘʟʏ ᴛᴇxᴛ', 'reply_txt'), InlineKeyboardButton('ᴀʙᴏᴜᴛ ᴛᴇxᴛ', 'about_txt')],
        [InlineKeyboardButton('◂ ʙᴀᴄᴋ', 'settings')]]
    )
    await query.message.edit_text(msg, reply_markup=reply_markup)

async def handle_text_update(client, query, key, prompt):
    await query.answer()
    try:
        ask_text = await client.ask(query.from_user.id, prompt, filters=filters.text, timeout=60)
        text = ask_text.text
        if text.lower() == 'cancel':
            await ask_text.reply("🚫 Action cancelled. No changes were made.")
            await texts(client, query)
            return

        if key == 'REPLY':
            client.reply_text = text
        else:
            client.messages[key] = text
        
        await client.mongodb.save_settings(client.name, client.get_current_settings())
        await ask_text.reply(f"✅ **{key.replace('_', ' ').title()}** has been updated successfully!")
        await texts(client, query)
    except ListenerTimeout:
        await query.message.reply("**Timeout! No changes were made.**")
    except Exception as e:
        client.LOGGER(__name__, client.name).error(e)
        await query.message.reply(f"An error occurred: {e}")

@Client.on_callback_query(filters.regex("^start_txt$"))
async def start_txt(client: Client, query: CallbackQuery):
    await handle_text_update(client, query, 'START', "Send the new **Start Message** text. Type `cancel` to abort.")

@Client.on_callback_query(filters.regex("^fsub_txt$"))
async def force_txt(client: Client, query: CallbackQuery):
    await handle_text_update(client, query, 'FSUB', "Send the new **Force Subscribe** text. Type `cancel` to abort.")

@Client.on_callback_query(filters.regex("^about_txt$"))
async def about_txt(client: Client, query: CallbackQuery):
    await handle_text_update(client, query, 'ABOUT', "Send the new **About Message** text. Type `cancel` to abort.")

@Client.on_callback_query(filters.regex("^reply_txt$"))
async def reply_txt(client: Client, query: CallbackQuery):
    await handle_text_update(client, query, 'REPLY', "Send the new default **Reply Message** text for unauthorized users. Type `cancel` to abort.")
