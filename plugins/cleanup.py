import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import UserIsBlocked, InputUserDeactivated, PeerIdInvalid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from bot import Bot

IST = ZoneInfo("Asia/Kolkata")

async def run_cleanup_and_notify(client: Bot):
    """
    This is the master function for cleaning up and notifying expired users.
    It returns a dictionary with detailed stats about the process.
    """
    log = client.LOGGER(__name__, "CLEANUP_FUNC")
    log.info("Starting cleanup and notification process...")
    
    now_utc = datetime.now(timezone.utc)
    all_pro_users = await client.mongodb.get_pros_list()
    
    if not all_pro_users:
        log.info("No pro users to process. Exiting cleanup.")
        return {"total_pro_users": 0, "permanent_users": 0, "active_expiring_users": 0, "expired_users_found": 0, "cleaned_count": 0}

    expired_user_ids = []
    permanent_users_count = 0
    active_expiring_users_count = 0
    
    for user_doc in all_pro_users:
        user_id = user_doc['_id']
        expires_at = user_doc.get('expires_at')
        
        # Skip permanent users
        if not expires_at:
            permanent_users_count += 1
            continue

        # Ensure the timestamp from DB is timezone-aware
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        if expires_at < now_utc:
            log.warning(f"User {user_id} has EXPIRED. Expiry date: {expires_at}.")
            expired_user_ids.append(user_id)
        else:
            active_expiring_users_count += 1

    cleaned_count = 0
    if expired_user_ids:
        log.info(f"Identified {len(expired_user_ids)} expired users. Proceeding with notification and removal.")
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
    
    stats = {
        "total_pro_users": len(all_pro_users),
        "permanent_users": permanent_users_count,
        "active_expiring_users": active_expiring_users_count,
        "expired_users_found": len(expired_user_ids),
        "cleaned_count": cleaned_count
    }
    return stats


@Client.on_message(filters.command('cleanup') & filters.private)
async def manual_cleanup_command(client: Bot, message: Message):
    """A command for the owner to manually trigger the cleanup process with a detailed report."""
    if message.from_user.id != client.owner:
        return await message.reply("❌ **This command is for the owner only.**")
        
    progress_msg = await message.reply("⚙️ **Running cleanup...**\n\nChecking the database for expired premium users. Please wait.")
    
    stats = await run_cleanup_and_notify(client)
    
    # Building the report message
    report = f"✅ **Cleanup Process Complete!**\n\n"
    report += f"📊 **Scan Results:**\n"
    report += f"   - Total Premium Users Checked: `{stats['total_pro_users']}`\n"
    report += f"   - Permanent Subscriptions: `{stats['permanent_users']}`\n"
    report += f"   - Active (Time-based) Subs: `{stats['active_expiring_users']}`\n"
    report += f"   - Expired Users Found: `{stats['expired_users_found']}`\n\n"
    
    if stats['cleaned_count'] > 0:
        report += f"🗑️ **Action Taken:**\n   - Successfully removed `{stats['cleaned_count']}` expired user(s) from the database."
    elif stats['total_pro_users'] > 0 and stats['expired_users_found'] == 0:
        report += f"👍 **No Action Needed:**\n   - All premium users are currently active. No one to remove."
    elif stats['total_pro_users'] == 0:
        report += f"ℹ️ **No Action Needed:**\n   - There are no premium users in the database to check."
    else:
        report += f"⚠️ **Action Status:**\n   - No users were removed."
        
    await progress_msg.edit_text(report)
