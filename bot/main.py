from aiogram import Bot, Dispatcher

import logging

from bot.misc import env_config_reader
from bot.handlers import user, admin


async def start_bot():
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=env_config_reader.settings.bot_token.get_secret_value())
    dp = Dispatcher()

    dp.include_routers(user.router, admin.router)
    
    await bot.delete_webhook(drop_pending_updates=True) # Do not answer to old messages that were sent when the bot was disabled

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()