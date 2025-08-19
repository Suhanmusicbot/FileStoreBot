#(©)AnimeYugen

from aiohttp import web
from plugins import web_server

from pyrogram import Client
from pyrogram.enums import ParseMode
import sys
from datetime import datetime
from config import LOGGER, PORT, OWNER_ID
from helper import MongoDB

version = "v1.0.0"


class Bot(Client):
    def __init__(self, session, workers, db, fsub, token, admins, messages, auto_del, db_uri, db_name, api_id, api_hash, protect, disable_btn):
        super().__init__(
            name=session,
            api_hash=api_hash,
            api_id=api_id,
            plugins={
                "root": "plugins"
            },
            workers=workers,
            bot_token=token
        )
        self.LOGGER = LOGGER
        self.name = session
        self.db = db
        self.fsub = fsub
        self.owner = OWNER_ID
        self.fsub_dict = {}
        self.admins = admins + [OWNER_ID] if OWNER_ID not in admins else admins
        self.messages = messages
        self.auto_del = auto_del
        self.protect = protect
        self.req_fsub = {}
        self.disable_btn = disable_btn
        self.reply_text = messages.get('REPLY', 'Do not send any useless message in the bot.')
        self.mongodb = MongoDB(db_uri, db_name)
        self.req_channels = []
    
    def get_current_settings(self):
        """Returns a dictionary of the current settings to be saved."""
        return {
            "admins": self.admins,
            "messages": self.messages,
            "auto_del": self.auto_del,
            "protect": self.protect,
            "disable_btn": self.disable_btn,
            "reply_text": self.reply_text,
            "fsub": self.fsub
        }

    async def start(self):
        await super().start()
        usr_bot_me = await self.get_me()
        self.uptime = datetime.now()

        # Load persisted settings from MongoDB
        saved_settings = await self.mongodb.load_settings(self.name)
        if saved_settings:
            self.LOGGER(__name__, self.name).info("Found saved settings in database. Loading them.")
            self.admins = saved_settings.get("admins", self.admins)
            self.messages = saved_settings.get("messages", self.messages)
            self.auto_del = saved_settings.get("auto_del", self.auto_del)
            self.protect = saved_settings.get("protect", self.protect)
            self.disable_btn = saved_settings.get("disable_btn", self.disable_btn)
            self.reply_text = saved_settings.get("reply_text", self.reply_text)
            self.fsub = saved_settings.get("fsub", self.fsub)
        else:
            self.LOGGER(__name__, self.name).info("No saved settings found. Using initial config from setup.json.")

        # Re-initialize fsub_dict with the correct fsub list
        self.fsub_dict = {}
        if len(self.fsub) > 0:
            for channel in self.fsub:
                try:
                    chat = await self.get_chat(channel[0])
                    name = chat.title
                    link = None
                    if not channel[1]: # if request is False
                        try:
                           link = chat.invite_link
                        except AttributeError: # If invite link is not available
                           pass
                    if not link and channel[2] <= 0: # If no link and no timer
                        chat_link = await self.create_chat_invite_link(channel[0], creates_join_request=channel[1])
                        link = chat_link.invite_link
                    
                    self.fsub_dict[channel[0]] = [name, link, channel[1], channel[2]]
                    if channel[1]:
                        self.req_channels.append(channel[0])

                except Exception as e:
                    self.LOGGER(__name__, self.name).warning(f"Bot can't Export Invite link from Force Sub Channel {channel[0]}! Error: {e}")
                    # Continue without this channel instead of stopping the bot
            await self.mongodb.set_channels(self.req_channels)

        try:
            db_channel = await self.get_chat(self.db)
            self.db_channel = db_channel
            test = await self.send_message(chat_id = db_channel.id, text = "Testing Message by @VOATcb")
            await test.delete()
        except Exception as e:
            self.LOGGER(__name__, self.name).warning(e)
            self.LOGGER(__name__, self.name).warning(f"Make Sure bot is Admin in DB Channel, and Double check the database channel Value, Current Value {self.db}")
            self.LOGGER(__name__, self.name).info("\nBot Stopped. Join https://t.me/Yugen_Bots_Support for support")
            sys.exit()

        self.LOGGER(__name__, self.name).info("Bot Started!!")
        self.username = usr_bot_me.username

    async def stop(self, *args):
        await super().stop()
        self.LOGGER(__name__, self.name).info("Bot stopped.")


async def web_app():
    app = web.AppRunner(await web_server())
    await app.setup()
    bind_address = "0.0.0.0"
    await web.TCPSite(app, bind_address, PORT).start()
