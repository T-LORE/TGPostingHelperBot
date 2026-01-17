from contextlib import suppress

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from bot.misc.states import AdminPanel
from bot.misc.callbacks import AdminCB
import bot.windows.admin as window
import bot.services.admin as service

router = Router()

@router.message(
        Command("start")
        )
async def cmd_start(message: Message, state: FSMContext):
    message_text, reply_markup = await window.get_main_menu_window()
    
    await message.answer(message_text,
    reply_markup=reply_markup)

    await state.set_state(AdminPanel.main_page)

@router.callback_query(
        F.data == AdminCB.UPDATE
        )
async def update_main_page(callback: CallbackQuery):
    message_text, reply_markup = await window.get_main_menu_window()
        
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(message_text, reply_markup=reply_markup)
    
    await callback.answer()

@router.message(
        AdminPanel.main_page,
        F.photo | F.video | F.animation
        )
async def handle_media_content(message: Message, album: list[Message] = None):
    files_to_process = album if album else [message]
    response = await service.enqueue_messages_media(files_to_process)

    message_text, reply_markup  = await window.get_message_enqueue_answer(response["posts"])

    await message.reply(message_text, reply_markup=reply_markup)

@router.callback_query(F.data == AdminCB.RETURN_MAIN)
@router.callback_query(F.data == AdminCB.RETURN_MAIN_EDIT)
@router.callback_query(F.data == AdminCB.RETURN_MAIN_DELETE)
async def return_to_main_page(callback: CallbackQuery, state: FSMContext):
    message_text, reply_markup = await window.get_main_menu_window()

    if callback.data == AdminCB.RETURN_MAIN_EDIT:
        with suppress(TelegramBadRequest):
            await callback.message.edit_text(message_text, reply_markup=reply_markup)
    elif callback.data == AdminCB.RETURN_MAIN_DELETE:
        await callback.message.delete()
        await callback.message.answer(message_text, reply_markup=reply_markup)
    elif callback.data == AdminCB.RETURN_MAIN:
        await callback.message.answer(message_text, reply_markup=reply_markup)
        
    await state.set_state(AdminPanel.main_page)

    await callback.answer()