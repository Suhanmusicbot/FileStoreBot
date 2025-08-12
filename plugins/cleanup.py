import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import UserIsBlocked, InputUserDeactivated, PeerIdInvalid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from bot import Bot
from config import OWNER_ID

IST = ZoneInfo("Asia/Kolkata")

async def run_cleanup_and_notify(client: Bot):
    """
    This is the master function for cleaning up and notifying expired users.
    It can be called by a manual command or a background task.
    It returns the number of users that were cleaned up.
    """
    log = client.LOGGER(__name__, "CLEANUP_FUNC")
    log.info("Starting cleanup and notification process...")
    
    now_utc = datetime.now(timezone.utc)
    log.info(f"Current reference time (UTC): {now_utc}")

    all_pro_users = await client.mongodb.get_pros_list()
    log.info(f"Found a total of {len(all_pro_users)} pro users in the database.")
    
    if not all_pro_users:
        log.info("No pro users to process. Exiting cleanup.")
        return 0

    expired_user_ids = []
    
    for user_doc in all_pro_users:
        user_id = user_doc['_id']
        expires_at = user_doc.get('expires_at')
        
        # Skip permanent users
        if not expires_at:
            log.info(f"User {user_id} is permanent. Skipping.")
            continue

        # Ensure the timestamp from DB is timezone-aware
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        if expires_at < now_utc:
            log.warning(f"User {user_id} has EXPIRED. Expiry date: {expires_at}.")
            expired_user_ids.append(user_id)
        else:
            log.info(f"User {user_id} is still ACTIVE. Expiry date: {expires_at}.")

    if not expired_user_ids:
        log.info("No users have expired. Cleanup complete.")
        return 0

    log.info(f"Identified {len(expired_user_ids)} expired users. Proceeding with notification and removal.")
    
    cleaned_count = 0
    for user_id in expired_user_ids:
        # 1. Send Notification
        try:
            await client.send_message(
                chat_id=user_id,
                text="⌛ **Your Premium subscription has expired.**\n\nYou are now on the free plan. To renew your subscription, please contact the owner."
            )
            log.info(f"Successfully sent expiration notice to user {user_id}.")
        except (UserIsBlocked, InputUserDeactivated, PeerIdInvalid):
            log.warning(f"Could not notify user {user_id} (user blocked, deactivated, or invalid).")
        except Exception as e:
            log.error(f"An unexpected error occurred while notifying user {user_id}: {e}")

        # 2. Remove from Database
        await client.mongodb.remove_pro(user_id)
        log.info(f"Removed user {user_id} from the pro list.")
        cleaned_count += 1
        await asyncio.sleep(1) # Small delay to avoid hitting rate limits

    log.info(f"Cleanup process finished. {cleaned_count} users were processed.")
    return cleaned_count


@Client.on_message(filters.command('cleanup') & filters.private)
async def manual_cleanup_command(client: Bot, message: Message):
    """A command for the owner to manually trigger the cleanup process."""
    if message.from_user.id != OWNER_ID:
        return await message.reply("❌ This command is for the owner only.")
        
    await message.reply("⚙️ **Starting manual cleanup of expired users...**\n\nCheck the bot logs for a detailed report.")
    
    cleaned_count = await run_cleanup_and_notify(client)
    
    if cleaned_count > 0:
        await message.reply(f"✅ **Cleanup complete.**\nRemoved {cleaned_count} expired users from the database.")
    else:
        await message.reply("✅ **Cleanup complete.**\nNo expired users were found.")
