from contextlib import suppress

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.misc.states import AdminPanel
from bot.misc.callbacks import AdminCB, DeletePostCB
import bot.windows.admin as window
import bot.services.admin as service
from bot.misc.util import parse_posts_from_message

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

@router.callback_query(
        F.data == AdminCB.UPDATE_TG_SCHEDULE,
        )
async def update_tg_schedule(callback: CallbackQuery):
    with suppress(TelegramBadRequest):
        await callback.message.edit_text("Обновление отложки...")
    
    posted, not_posted = await service.update_tg_schedule()

    builder = InlineKeyboardBuilder()
    return_btn = InlineKeyboardButton(text="Вернуться на главную", callback_data=AdminCB.RETURN_MAIN_EDIT),
    builder.row(*return_btn)

    await callback.message.edit_text(f"Обновление завершено: {len(posted)} постов отправлено, {len(not_posted)} не отправлено", reply_markup=builder.as_markup())

@router.message(
        StateFilter(AdminPanel.main_page, None),
        F.photo | F.video | F.animation
        )
async def handle_media_content(message: Message, album: list[Message] = None):
    files_to_process = album if album else [message]

    response = await service.enqueue_messages_media_by_timestamps(files_to_process)


    message_text, reply_markup  = await window.get_message_enqueue_answer(response["posts"])

    await message.reply(message_text, reply_markup=reply_markup)

@router.callback_query(
    StateFilter(AdminPanel.main_page, None),
    DeletePostCB.filter(F.source == "mass_posting")
)
async def delete_from_view(callback: CallbackQuery, callback_data: DeletePostCB, state: FSMContext):
    post_id = callback_data.id
    
    is_deleted = await service.delete_post_from_queue(post_id)

    if not is_deleted:
        await callback.answer("Не удалось удалить пост", show_alert=True)
        return
    
    current_posts_list = parse_posts_from_message(callback.message)
    
    if not current_posts_list:
        await callback.answer("Не удалось прочитать список постов из сообщения", show_alert=True)
        return

    post_found = False
    for post in current_posts_list:
        if post.get("post_id") == post_id:
            post["status"] = "DELETED"
            post_found = True
            break
    
    if not post_found:
        await callback.answer("Ошибка обновления списка (ID не найден в тексте)", show_alert=True)
        return

    message_text, reply_markup = await window.get_message_enqueue_answer(current_posts_list)
    

    await callback.message.edit_text(text=message_text, reply_markup=reply_markup)
    
    await callback.answer("Пост удален")
    
    
    


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