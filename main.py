import asyncio
import json
from bot import Bot, web_app
from pyrogram import idle
from plugins.cleanup import run_cleanup_and_notify

# --- Background Task for Database Cleanup ---
async def cleanup_task(bot_instance):
    """A background task that runs the master cleanup function periodically."""
    while True:
        # Wait for 1 hour (3600 seconds) before the next automatic cleanup.
        # Use the /cleanup command for immediate, on-demand checks.
        await asyncio.sleep(3600)
        
        bot_instance.LOGGER(__name__, bot_instance.session_name).info("BACKGROUND_TASK: Triggering scheduled cleanup.")
        await run_cleanup_and_notify(bot_instance)
        bot_instance.LOGGER(__name__, bot_instance.session_name).info("BACKGROUND_TASK: Scheduled cleanup finished.")


# Static default fallback message templates
default_messages = {
    'START': '<b>Hi There...! 💥\n\nI am a file-store bot.\nI can generate links directly with no problems\nMy Owner: @MRSungCHinwOO/b>',
    'FSUB': '',
    'ABOUT': 'ABOUT MSG',
    'REPLY': 'reply_text',
    'START_PHOTO': '',
    'FSUB_PHOTO': ''
}

async def main():
    apps = []
    
    with open("setup.json", "r") as f:
        setups = json.load(f)

    for config in setups:
        bot_instance = Bot(
            session=config["session"],
            workers=config.get("workers", 8),
            db=config["db"],
            fsub=config.get("fsubs", []),
            token=config["token"],
            admins=config.get("admins", []),
            messages=config.get("messages", default_messages),
            auto_del=config.get("auto_del", 0),
            db_uri=config["db_uri"],
            db_name=config["db_name"],
            api_id=int(config["api_id"]),
            api_hash=config["api_hash"],
            protect=config.get("protect", False),
            disable_btn=config.get("disable_btn", True),
            bypass_timeout=config.get("bypass_timeout", 50)
        )
        apps.append(bot_instance)

    # Start all bot clients in parallel
    await asyncio.gather(*[app.start() for app in apps])

    # Schedule the background tasks to run concurrently
    tasks = []
    for app in apps:
        tasks.append(asyncio.create_task(cleanup_task(app)))

    print("All bots and background tasks have started successfully!")
    
    # Keep the main process alive while tasks run in the background
    await idle()

    # The following code will only run on shutdown (e.g., Ctrl+C)
    print("Shutting down bots...")
    await asyncio.gather(*[app.stop() for app in apps])


async def runner():
    # Run the main bot logic and the web server concurrently
    await asyncio.gather(
        main(),
        web_app()
    )

if __name__ == "__main__":
    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        print("\nBot stopped manually.")
