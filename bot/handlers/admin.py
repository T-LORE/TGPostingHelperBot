import datetime

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters.command import Command

from bot.filters.admin import IsAdmin
from bot.middlewares.album import AlbumMiddleware
from bot.database.requests import add_to_queue
from bot.misc.env_config_reader import settings
from bot.misc.util import get_next_posts_datetime

router = Router()
router.message.filter(IsAdmin())
router.message.middleware(AlbumMiddleware(latency=0.5))

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Hello world, Admin!")

@router.message(F.photo | F.video | F.animation)
async def handle_media_content(message: Message, album: list[Message] = None):
    files_to_process = album if album else [message]
    added_count = 0

    dates_list = await get_next_posts_datetime(len(files_to_process))

    for msg, publish_date in zip(files_to_process, dates_list):
        file_id = None
        media_type = 'photo'
        
        if msg.photo:
            file_id = msg.photo[-1].file_id
            media_type = 'photo'
        elif msg.video:
            file_id = msg.video.file_id
            media_type = 'video'
        elif msg.animation:
            file_id = msg.animation.file_id
            media_type = 'animation'
            
        if file_id:
            await add_to_queue(file_id=file_id, caption=settings.post_caption, media_type=media_type, publish_date=publish_date)
            added_count += 1

    await message.reply(f"✅ Добавлено {added_count} медиафайлов в очередь!")

@router.message()
async def echo_gif(message: Message):
    await message.reply("Сообщение не обработано!")