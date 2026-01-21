from contextlib import suppress

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from bot.misc.states import AdminPanel
from bot.misc.callbacks import AdminCB
import bot.windows.admin as window
import bot.services.admin as service

router = Router()

@router.callback_query(
        F.data == AdminCB.DELETE_ALL_CONFIRM
        )
async def delete_all_posts_confirmation(callback: CallbackQuery, state: FSMContext):
    message_text, reply_markup = await window.get_delete_all_posts_confirmation()
    
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(message_text, reply_markup=reply_markup)
    
    await state.set_state(AdminPanel.delete_posts_confirmation)

    await callback.answer()

@router.callback_query(
        AdminPanel.delete_posts_confirmation,
        F.data == AdminCB.DELETE_ALL
        )
async def delete_all_posts(callback: CallbackQuery, state: FSMContext):
    results = await service.delete_all_posts_from_queue()

    message_text, reply_markup = await window.get_main_menu_window()
    
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(message_text, reply_markup=reply_markup)

    await state.set_state(AdminPanel.main_page)

    is_positive = all([res['status'] == 'DELETED' for res in results])
    if not is_positive:
        await callback.answer(f"Не удалось удалить все посты", show_alert=True)
    else:
        await callback.answer("Все посты были удалены!", show_alert=True)