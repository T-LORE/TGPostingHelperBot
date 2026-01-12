import datetime

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from bot.filters.admin import IsAdmin
from bot.middlewares.album import AlbumMiddleware
from bot.database.requests import add_to_queue, get_queue_count, get_earliest_post
from bot.misc.env_config_reader import settings
from bot.misc.util import get_next_posts_datetime

router = Router()
router.message.filter(IsAdmin())
router.message.middleware(AlbumMiddleware(latency=0.5))

class AdminPanel(StatesGroup):
    main_page = State()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await message.answer(f"""
    📱 ГЛАВНОЕ МЕНЮ / СТАТИСТИКА
    -------------------
    Админ: user_id - role_id
    Управляемая группа: group_id
                         
    В очереди: {await get_queue_count()} поста
    След. пост: {(await get_earliest_post())["publish_date"]}

    Всего сделано постов: metrics_post_count
    Постов отменено: metrics_post_canceled
    -------------------
    (Жду файлы для загрузки...)""")
    await state.set_state(AdminPanel.main_page)

@router.message(
        AdminPanel.main_page,
        F.photo | F.video | F.animation
        )
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