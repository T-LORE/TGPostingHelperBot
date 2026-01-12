from contextlib import suppress

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.exceptions import TelegramBadRequest

from bot.filters.admin import IsAdmin
from bot.middlewares.album import AlbumMiddleware
from bot.database.requests import add_to_queue
from bot.misc.env_config_reader import settings
from bot.misc.util import get_next_posts_datetime
from bot.windows.admin import *

router = Router()
router.message.filter(IsAdmin())
router.message.middleware(AlbumMiddleware(latency=0.5))

class AdminPanel(StatesGroup):
    main_page = State()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    message_text, reply_markup = await get_main_menu_window()
    
    await message.answer(message_text,
    reply_markup=reply_markup)

    await state.set_state(AdminPanel.main_page)

@router.callback_query(F.data == "update_main_page")
async def update_main_page(callback: CallbackQuery):
    message_text, reply_markup = await get_main_menu_window()
        
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(message_text, reply_markup=reply_markup)
    
    await callback.answer()

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
async def unknown_command(message: Message):
    message_text, reply_markup = await get_unknown_comman_window()
    await message.reply(message_text,
    reply_markup=reply_markup)

@router.callback_query(F.data == "return_to_main_page")
async def update_main_page(callback: CallbackQuery):
    message_text, reply_markup = await get_main_menu_window()

    await callback.message.answer(message_text, reply_markup=reply_markup)
    
    await callback.message.delete()
    
    await callback.answer()