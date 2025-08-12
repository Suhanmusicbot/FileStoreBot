from aiohttp import web
from plugins import web_server
from pyrogram import Client
from pyrogram.enums import ParseMode
import sys
from datetime import datetime
from config import LOGGER, PORT, OWNER_ID, SHORT_URL, SHORT_API
from helper import MongoDB

version = "v1.0.0"

class Bot(Client):
    def __init__(self, session, workers, db, fsub, token, admins, messages, auto_del, db_uri, db_name, api_id, api_hash, protect, disable_btn, bypass_timeout):
        super().__init__(
            name=session,
            api_hash=api_hash,
            api_id=api_id,
            plugins={"root": "plugins"},
            workers=workers,
            bot_token=token
        )
        self.LOGGER = LOGGER
        # Store initial config to save to DB on first run
        self.initial_config = {
            "session": session, "workers": workers, "db": db, "fsub": fsub,
            "token": token, "admins": admins, "messages": messages, "auto_del": auto_del,
            "db_uri": db_uri, "db_name": db_name, "api_id": api_id, "api_hash": api_hash,
            "protect": protect, "disable_btn": disable_btn, "short_url": SHORT_URL, "short_api": SHORT_API
        }
        
        self.session_name = session
        self.owner = OWNER_ID
        self.mongodb = MongoDB(db_uri, db_name, self.LOGGER)
        self.uptime = datetime.now()
        self.req_channels = []
        self.fsub_dict = {}
        self.bypass_timeout = bypass_timeout
        self.user_cache = {} # In-memory cache for user state

    # Method to get all current settings as a dictionary for saving
    def get_current_settings(self):
        return {
            "admins": self.admins,
            "messages": self.messages,
            "auto_del": self.auto_del,
            "protect": self.protect,
            "disable_btn": self.disable_btn,
            "reply_text": self.reply_text,
            "fsub": self.fsub,
            "short_url": self.short_url,
            "short_api": self.short_api
        }

    async def start(self):
        await super().start()
        
        # Load settings from DB
        saved_settings = await self.mongodb.load_settings(self.session_name)
        
        if saved_settings:
            # If settings found in DB, load them
            self.LOGGER(__name__, self.session_name).info("Settings loaded from database.")
            self.admins = saved_settings.get("admins", self.initial_config['admins'])
            self.messages = saved_settings.get("messages", self.initial_config['messages'])
            self.auto_del = saved_settings.get("auto_del", self.initial_config['auto_del'])
            self.protect = saved_settings.get("protect", self.initial_config['protect'])
            self.disable_btn = saved_settings.get("disable_btn", self.initial_config['disable_btn'])
            self.fsub = saved_settings.get("fsub", self.initial_config['fsub'])
            self.short_url = saved_settings.get("short_url", self.initial_config['short_url'])
            self.short_api = saved_settings.get("short_api", self.initial_config['short_api'])
            self.reply_text = saved_settings.get("reply_text", self.initial_config['messages'].get('REPLY', ''))
        else:
            # If no settings in DB (first run), load from initial config and save to DB
            self.LOGGER(__name__, self.session_name).info("No settings found in DB. Loading from file and saving.")
            self.admins = self.initial_config['admins']
            self.messages = self.initial_config['messages']
            self.auto_del = self.initial_config['auto_del']
            self.protect = self.initial_config['protect']
            self.disable_btn = self.initial_config['disable_btn']
            self.fsub = self.initial_config['fsub']
            self.short_url = self.initial_config['short_url']
            self.short_api = self.initial_config['short_api']
            self.reply_text = self.initial_config['messages'].get('REPLY', '')
            # Save the initial settings
            await self.mongodb.save_settings(self.session_name, self.get_current_settings())

        # Add owner to admins list
        if self.owner not in self.admins:
            self.admins.append(self.owner)

        usr_bot_me = await self.get_me()
        
        # Initialize F-Sub channels
        if len(self.fsub) > 0:
            for channel in self.fsub:
                try:
                    chat = await self.get_chat(channel[0])
                    name = chat.title
                    link = chat.invite_link or (await self.create_chat_invite_link(channel[0], creates_join_request=channel[1])).invite_link
                    
                    self.fsub_dict[channel[0]] = [name, link, channel[1], channel[2]] # [name, link, request_bool, timer]

                    if channel[1]: # if request is True
                        self.req_channels.append(channel[0])
                except Exception as e:
                    self.LOGGER(__name__, self.session_name).warning(f"F-Sub error for channel {channel[0]}: {e}")
            await self.mongodb.set_channels(self.req_channels)

        # Check DB Channel
        try:
            self.db = self.initial_config['db']
            self.db_channel = await self.get_chat(self.db)
            test = await self.send_message(chat_id=self.db_channel.id, text="Bot testing message...")
            await test.delete()
        except Exception as e:
            self.LOGGER(__name__, self.session_name).warning(e)
            self.LOGGER(__name__, self.session_name).warning(f"Make sure bot is Admin in DB Channel: {self.db}")
            sys.exit()
            
        self.username = usr_bot_me.username
        self.LOGGER(__name__, self.session_name).info("Bot Started Successfully!")

    async def stop(self, *args):
        await super().stop()
        self.LOGGER(__name__, self.session_name).info("Bot stopped.")

async def web_app():
    app = web.AppRunner(await web_server())
    await app.setup()
    bind_address = "0.0.0.0"
    await web.TCPSite(app, bind_address, PORT).start()
