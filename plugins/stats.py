from pyrogram import Client, filters
from pyrogram.types import Message
from datetime import datetime, timedelta

@Client.on_message(filters.command('stats') & filters.private)
async def stats_command(client: Client, message: Message):
    # Only admins can use this command
    if message.from_user.id not in client.admins:
        return await message.reply("You do not have permission to use this command.")

    try:
        today_clicks, yesterday_clicks = await client.mongodb.get_stats()
        
        # Get total users
        total_users = await client.mongodb.full_userbase()
        
        stats_message = (
            f"📊 **Bot & Shortener Statistics**\n\n"
            f"👤 **User Base:**\n"
            f"   - Total Users: `{len(total_users)}`\n\n"
            f"🔗 **Shortener Clicks:**\n"
            f"   - **Today:** `{today_clicks}` clicks\n"
            f"   - **Yesterday:** `{yesterday_clicks}` clicks"
        )

        await message.reply_text(stats_message)

    except Exception as e:
        client.LOGGER(__name__, client.name).error(f"Error fetching stats: {e}")
        await message.reply_text("An error occurred while fetching statistics.")
