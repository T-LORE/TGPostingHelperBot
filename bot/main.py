from aiogram import Bot, Dispatcher

import logging

from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.misc.config import env, config
from bot.handlers.admin import admin_router
from bot.database import start_db

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bot.services.schedule_poster import start_telethon, stop_telethon, upload_posts_to_schedule
from bot.misc.logger import configure_logger

async def start_bot():
    configure_logger()
    
    bot = Bot(
        token=env.bot_token.get_secret_value(),
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        )
    )
    dp = Dispatcher()

    await start_db()

    dp.include_routers(admin_router)
    
    await bot.delete_webhook(drop_pending_updates=True) # Do not answer to old messages that were sent when the bot was disabled

    await start_telethon()

    # scheduler = AsyncIOScheduler()
    # scheduler.add_job(upload_posts_to_schedule, "interval", minutes=5)
    # scheduler.start()
    
    await upload_posts_to_schedule()
    
    try:
        await dp.start_polling(bot)
    finally:
        # await stop_telethon()
        await bot.session.close()