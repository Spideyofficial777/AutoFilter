import sys
import glob
import importlib
from pathlib import Path
from pyrogram import idle
import logging
import logging.config
import time  
import asyncio
import pytz
from aiohttp import web
from datetime import date, datetime
from pyrogram import Client, __version__
from pyrogram.raw.all import layer
from database.ia_filterdb import Media, Media2, tempDict, choose_mediaDB, db as clientDB
from database.users_chats_db import db
from info import *
from utils import temp
from typing import Union, Optional, AsyncGenerator
from pyrogram import types
from Script import script 
from plugins import web_server, check_expired_premium
from LucyBot import CodeflixBot
from util.keepalive import ping_server
from LucyBot.clients import initialize_clients

# Logging Configuration
logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("imdbpy").setLevel(logging.ERROR)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("aiohttp").setLevel(logging.ERROR)
logging.getLogger("aiohttp.web").setLevel(logging.ERROR)

botStartTime = time.time()
ppath = "plugins/*.py"
files = glob.glob(ppath)

async def Lucy_start():
    print("\nInitializing Lucy Bot...")
    
    # Ensure bot is properly started
    await CodeflixBot.start()
    bot_info = await CodeflixBot.get_me()
    CodeflixBot.username = bot_info.username

    # Initialize Clients
    await initialize_clients()

    # Load Plugins
    for name in files:
        with open(name) as a:
            patt = Path(a.name)
            plugin_name = patt.stem.replace(".py", "")
            plugins_dir = Path(f"plugins/{plugin_name}.py")
            import_path = f"plugins.{plugin_name}"
            spec = importlib.util.spec_from_file_location(import_path, plugins_dir)
            load = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(load)
            sys.modules[f"plugins.{plugin_name}"] = load
            print(f"Lucy Imported => {plugin_name}")

    # Heroku Server Ping
    if ON_HEROKU:
        asyncio.create_task(ping_server())

    # Ban List
    b_users, b_chats = await db.get_banned()
    temp.BANNED_USERS = b_users
    temp.BANNED_CHATS = b_chats

    # Database Check
    await Media.ensure_indexes()
    await Media2.ensure_indexes()
    stats = await clientDB.command('dbStats')
    free_dbSize = round(512 - ((stats['dataSize'] / (1024 * 1024)) + (stats['indexSize'] / (1024 * 1024))), 2)

    if DATABASE_URI2 and free_dbSize < 62:
        tempDict["indexDB"] = DATABASE_URI2
        logging.info(f"Primary DB only has {free_dbSize} MB left. Switching to Secondary DB.")
    elif DATABASE_URI2 is None:
        logging.error("Missing SECONDDB_URI! Add it now. Exiting...")
        exit()
    else:
        logging.info(f"Primary DB has enough space ({free_dbSize}MB). Using it for storage.")

    await choose_mediaDB()

    # Fetch Bot Details
    me = await CodeflixBot.get_me()
    temp.ME = me.id
    temp.U_NAME = me.username
    temp.B_NAME = me.first_name
    CodeflixBot.username = f'@{me.username}'

    # Expired Premium Check
    CodeflixBot.loop.create_task(check_expired_premium(CodeflixBot))

    logging.info(f"{me.first_name} started with Pyrogram v{__version__} (Layer {layer}) on {me.username}.")
    logging.info(LOG_STR)
    logging.info(script.LOGO)

    # Bot Restart Notification
    tz = pytz.timezone("Asia/Kolkata")
    today = date.today()
    now = datetime.now(tz)
    current_time = now.strftime("%H:%M:%S %p")

    await CodeflixBot.send_message(
        chat_id=LOG_CHANNEL,
        text=script.RESTART_TXT.format(today, current_time)
    )

    # Web Server Setup
    app = web.AppRunner(await web_server())
    await app.setup()
    bind_address = "0.0.0.0"
    await web.TCPSite(app, bind_address, PORT).start()

    # Keep Bot Running
    await idle()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()  # Fix event loop issue
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(Lucy_start())
    except KeyboardInterrupt:
        logging.info("Service Stopped. Bye 👋")
