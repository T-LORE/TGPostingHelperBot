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
import bot.windows.admin as window
import bot.services.admin as service

router = Router()
router.message.filter(IsAdmin())
router.message.middleware(AlbumMiddleware(latency=0.5))

class AdminPanel(StatesGroup):
    main_page = State()
    delete_posts_confirmation = State()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    message_text, reply_markup = await window.get_main_menu_window()
    
    await message.answer(message_text,
    reply_markup=reply_markup)

    await state.set_state(AdminPanel.main_page)

@router.callback_query(F.data == "update_main_page")
async def update_main_page(callback: CallbackQuery):
    message_text, reply_markup = await window.get_main_menu_window()
        
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(message_text, reply_markup=reply_markup)
    
    await callback.answer()

@router.callback_query(F.data == "delete_all_posts_confirmation")
async def delete_all_posts_confirmation(callback: CallbackQuery, state: FSMContext):
    message_text, reply_markup = await window.get_delete_all_posts_confirmation()
    
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(message_text, reply_markup=reply_markup)
    
    await state.set_state(AdminPanel.delete_posts_confirmation)

    await callback.answer()

@router.callback_query(
        AdminPanel.delete_posts_confirmation,
        F.data == "delete_all_posts")
async def delete_all_posts(callback: CallbackQuery, state: FSMContext):
    await service.delete_all_posts_from_queue()
    message_text, reply_markup = await window.get_main_menu_window()
    
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(message_text, reply_markup=reply_markup)

    await state.set_state(AdminPanel.main_page)
    
    await callback.answer("Все посты были удалены!", show_alert=True)

@router.message(
        AdminPanel.main_page,
        F.photo | F.video | F.animation
        )
async def handle_media_content(message: Message, album: list[Message] = None):
    files_to_process = album if album else [message]
    response = await service.enqueue_messages_media(files_to_process)

    message_text, reply_markup  = await window.get_message_enqueue_answer(response["posts_id"])

    await message.reply(message_text, reply_markup=reply_markup)

@router.message()
async def unknown_command(message: Message):
    message_text, reply_markup = await window.get_unknown_command_window()
    await message.reply(message_text,
    reply_markup=reply_markup)

@router.callback_query(F.data == "return_to_main_page")
@router.callback_query(F.data == "return_to_main_page_with_edit")
@router.callback_query(F.data == "return_to_main_page_with_delete")
async def return_to_main_page(callback: CallbackQuery, state: FSMContext):
    message_text, reply_markup = await window.get_main_menu_window()

    if callback.data == "return_to_main_page_with_edit":
        with suppress(TelegramBadRequest):
            await callback.message.edit_text(message_text, reply_markup=reply_markup)
    elif callback.data == "return_to_main_page_with_delete":
        await callback.message.delete()
        await callback.message.answer(message_text, reply_markup=reply_markup)
    elif callback.data == "return_to_main_page":
        await callback.message.answer(message_text, reply_markup=reply_markup)
        
    await state.set_state(AdminPanel.main_page)

    await callback.answer()