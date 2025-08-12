from pyrogram import Client, filters
from pyrogram.types import Message
from datetime import datetime, timedelta, timezone
from pyrogram.errors import PeerIdInvalid, UserIsBlocked, InputUserDeactivated
from zoneinfo import ZoneInfo

from bot import Bot

# Define the Indian Standard Time zone
IST = ZoneInfo("Asia/Kolkata")

#========================================================================#

@Client.on_message(filters.command('authorize') & filters.private)
async def add_admin_command(client: Bot, message: Message):
    if message.from_user.id != client.owner:
        await message.reply_text("❌ Only the Owner can use this command.")
        return

    if len(message.command) < 2:
        await message.reply_text(
            "<b>Usage:</b>\n/authorize <user_id> [duration] [s/m/h/d/y]\n\n"
            "<b>Examples:</b>\n"
            "/authorize 123456789 — permanent\n"
            "/authorize 123456789 2 d — 2 days"
        )
        return

    try:
        user_id_to_add = int(message.command[1])
    except ValueError:
        await message.reply_text("❌ Invalid user ID.")
        return

    expires_at_ist_display = None
    action_text = "Permanently authorized"
    is_permanent = True

    # Handle temporary subscription if duration is provided
    if len(message.command) == 4:
        is_permanent = False
        try:
            amount = int(message.command[2])
            unit = message.command[3].lower()
            delta = timedelta()

            if unit == "s": delta = timedelta(seconds=amount)
            elif unit == "m": delta = timedelta(minutes=amount)
            elif unit == "h": delta = timedelta(hours=amount)
            elif unit == "d": delta = timedelta(days=amount)
            elif unit == "y": delta = timedelta(days=amount * 365)
            else:
                return await message.reply_text("❌ Invalid time unit. Use: s/m/h/d/y.")

            now_ist = datetime.now(IST)
            start_date_ist = now_ist
            action_text = "Renewed"

            pro_doc = await client.mongodb.get_pro_user(user_id_to_add)
            if pro_doc:
                existing_expires_at = pro_doc.get('expires_at')
                if existing_expires_at:
                    existing_expires_at_ist = existing_expires_at.astimezone(IST)
                    if existing_expires_at_ist > now_ist:
                        start_date_ist = existing_expires_at_ist
                        action_text = "Extended"

            expires_at_ist_display = start_date_ist + delta
            expires_at_utc = expires_at_ist_display.astimezone(timezone.utc)
            await client.mongodb.add_pro(user_id_to_add, expires_at_utc)

        except Exception as e:
            await message.reply_text(f"❌ An error occurred during authorization: {e}")
            client.LOGGER(__name__, "AUTHORIZE").error(f"Error: {e}", exc_info=True)
            return
    else:
        # Handle permanent subscription
        await client.mongodb.add_pro(user_id_to_add, expires_at=None)

    # --- Notification Logic ---
    admin_reply_text = f"✅ User <code>{user_id_to_add}</code> subscription has been {action_text.lower()}"
    if expires_at_ist_display:
        admin_reply_text += f" until {expires_at_ist_display.strftime('%d %b %Y, %H:%M %Z')}."

    try:
        if is_permanent:
            await client.send_message(user_id_to_add, "🎉 **Congratulations!**\n\nYou have been granted **permanent** Premium access.")
        else:
            expiry_text = expires_at_ist_display.strftime('%d %b %Y at %I:%M %p %Z')
            await client.send_message(user_id_to_add, f"🎉 **Congratulations! You are now a Premium user.**\n\nYour access is valid until: **{expiry_text}**")
        
        admin_reply_text += "\n\n*User has been notified.*"
    except (UserIsBlocked, InputUserDeactivated, PeerIdInvalid):
        admin_reply_text += "\n\n*⚠️ Could not notify the user (they may have blocked the bot).* "
    except Exception as e:
        client.LOGGER(__name__, "AUTHORIZE_NOTIFY").error(f"Failed to notify user {user_id_to_add}: {e}")
        admin_reply_text += f"\n\n*⚠️ An unexpected error occurred while trying to notify the user.*"
    
    await message.reply_text(admin_reply_text)


#========================================================================#

@Client.on_message(filters.command('unauthorize') & filters.private)
async def remove_admin_command(client: Bot, message: Message):
    if message.from_user.id != client.owner:
        return await message.reply_text("Only the Owner can use this command...!")

    if len(message.command) != 2:
        return await message.reply_text("<b>You're using the wrong format. Do it like this:</b> /unauthorize <userid>")

    try:
        user_id_to_remove = int(message.command[1])
    except ValueError:
        return await message.reply_text("Invalid user ID. Please check again...!")

    if not await client.mongodb.get_pro_user(user_id_to_remove):
        return await message.reply_text(f"<b>User <code>{user_id_to_remove}</code> is not in the pro list.</b>")

    await client.mongodb.remove_pro(user_id_to_remove)
    
    user_name = f"<code>{user_id_to_remove}</code>"
    try:
        user = await client.get_users(user_id_to_remove)
        user_name = user.mention
    except (PeerIdInvalid, IndexError):
        pass

    await message.reply_text(f"<b>User {user_name} has been removed from pro users!</b>")

    try:
        await client.send_message(user_id_to_remove, "<b>Your membership has been ended.\n\nTo renew the membership, contact the owner.</b>")
    except (UserIsBlocked, InputUserDeactivated, PeerIdInvalid):
        await message.reply_text(f"⚠️ Could not notify the user (they may have blocked the bot or have a deactivated account).")
    except Exception as e:
        await message.reply_text(f"⚠️ An unexpected error occurred while trying to notify the user: {e}")


#========================================================================#

@Client.on_message(filters.command('authorized') & filters.private)
async def admin_list_command(client: Bot, message: Message):
    if message.from_user.id != client.owner:
        return await message.reply_text("Only the Owner can use this command...!")

    pro_user_docs = await client.mongodb.get_pros_list()
    
    active_users = []
    expired_user_ids_to_remove = []
    now_utc = datetime.now(timezone.utc)

    for user_doc in pro_user_docs:
        expires_at = user_doc.get('expires_at')
        if expires_at and isinstance(expires_at, datetime):
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            
            if expires_at < now_utc:
                expired_user_ids_to_remove.append(user_doc['_id'])
                continue
        
        active_users.append(user_doc)

    cleanup_notice = ""
    if expired_user_ids_to_remove:
        client.LOGGER(__name__, "AUTHORIZED_CMD").info(f"Found {len(expired_user_ids_to_remove)} expired users. Cleaning up now...")
        for user_id in expired_user_ids_to_remove:
            await client.mongodb.remove_pro(user_id)
        cleanup_notice = f"<i>(Cleaned up {len(expired_user_ids_to_remove)} expired users.)</i>\n\n"

    if not active_users:
        return await message.reply_text(f"{cleanup_notice}<b>No active authorized users found.</b>")

    formatted_users = []
    for user_doc in active_users:
        user_id = user_doc['_id']
        expires_at = user_doc.get('expires_at')
        expiry_text = "<b>Status:</b> Permanent"
        if expires_at and isinstance(expires_at, datetime):
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            ist_expires_at = expires_at.astimezone(IST)
            expiry_text = f"<b>Expires:</b> {ist_expires_at.strftime('%d %b %Y, %H:%M %Z')}"

        try:
            user = await client.get_users(user_id)
            full_name = user.first_name + (" " + user.last_name if user.last_name else "")
            username = f"@{user.username}" if user.username else "N/A"
            formatted_users.append(
                f"›› <b>{full_name}</b>\n"
                f"   - <b>ID:</b> <code>{user.id}</code>\n"
                f"   - <b>Username:</b> {username}\n"
                f"   - {expiry_text}"
            )
        except Exception:
            formatted_users.append(
                f"›› <b>User ID:</b> <code>{user_id}</code> (Info not fetchable)\n"
                f"   - {expiry_text}"
            )

    response_text = f"{cleanup_notice}<b>Authorized Users List:</b>\n\n" + "\n\n".join(formatted_users)
    for chunk in [response_text[i:i + 4096] for i in range(0, len(response_text), 4096)]:
        await message.reply_text(chunk, disable_web_page_preview=True)
