from contextlib import suppress
from datetime import datetime

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter

from bot.misc.states import AdminPanel
from bot.misc.callbacks import AdminCB, NavigationCB, DeletePostCB, ViewPostCB, DateViewCB
from bot.misc.util import send_post_media
from bot.database.requests import get_post
import bot.windows.admin as window
import bot.services.admin as service


router = Router()

@router.callback_query(
        F.data == AdminCB.POST_QUEUE
        )
async def post_queue(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminPanel.post_queue_page)
    message_text, reply_markup = await window.get_post_queue_window_start()

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(message_text, reply_markup=reply_markup)

    await state.update_data(list_msg_id=callback.message.message_id)

    await callback.answer()

@router.callback_query(
        AdminPanel.post_queue_page, 
        DateViewCB.filter()
        )
async def post_queue_navigation(callback: CallbackQuery, callback_data: NavigationCB):
    day = callback_data.day
    month = callback_data.month
    year = callback_data.year
    date = datetime(year, month, day)
    
    message_text, reply_markup = await window.get_post_queue_window(date)

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(message_text, reply_markup=reply_markup)
    
    await callback.answer()

@router.callback_query(
    AdminPanel.post_queue_page, 
    DeletePostCB.filter(F.source == "list")
)
async def delete_from_list(callback: CallbackQuery, callback_data: DeletePostCB, state: FSMContext):
    post_id = callback_data.id
    post = await get_post(post_id)
    date = None
    if post is not None:
        date = post["publish_date"]


    is_deleted = await service.delete_post_from_queue(post_id)

    if not is_deleted:
        await callback.answer("Не удалось удалить пост", show_alert=True)
        return

    state_data = await state.get_data()
    opened_post_id = state_data.get("opened_post_id")
    view_msg_id = state_data.get("opened_post_msg_id")

    if view_msg_id and opened_post_id == post_id:
        with suppress(TelegramBadRequest):
            await callback.message.bot.delete_message(
                chat_id=callback.message.chat.id,
                message_id=view_msg_id
            )
        await state.update_data(opened_post_msg_id=None, opened_post_id=None)

    message_text, reply_markup = await window.get_post_queue_window(date)
    
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(text=message_text, reply_markup=reply_markup)

    await callback.answer("Пост удален")

@router.callback_query(
    AdminPanel.post_queue_page, 
    DeletePostCB.filter(F.source == "view")
)
async def delete_from_view(callback: CallbackQuery, callback_data: DeletePostCB, state: FSMContext):
    post_id = callback_data.id
    post = await get_post(post_id)
    date = None
    if post is not None:
        date = post["publish_date"]

    is_deleted = await service.delete_post_from_queue(post_id)

    if not is_deleted:
        await callback.answer("Не удалось удалить пост", show_alert=True)
        return

    await state.update_data(opened_post_msg_id=None, opened_post_id=None)

    state_data = await state.get_data()
    list_msg_id = state_data.get("list_msg_id")

    if list_msg_id:
        message_text, reply_markup = await window.get_post_queue_window(date)
        
        with suppress(TelegramBadRequest):
            await callback.message.bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=list_msg_id,
                text=message_text,
                reply_markup=reply_markup
            )

    await callback.answer("Пост удален", show_alert=True)

    await callback.message.delete()

@router.callback_query(
        AdminPanel.post_queue_page, 
        ViewPostCB.filter()
        )
async def view_post_btn_clicked(callback: CallbackQuery, callback_data: ViewPostCB, state: FSMContext):
    post_id = callback_data.id
    current_page = callback_data.page
    
    data = await window.get_post_view_window(post_id, current_page)

    if data is None:
        await callback.answer("Пост не найден")
        return
    
    state_data = await state.get_data()
    old_view_msg_id = state_data.get("opened_post_msg_id")

    if old_view_msg_id:
        with suppress(TelegramBadRequest):
            await callback.message.bot.delete_message(
                chat_id=callback.message.chat.id,
                message_id=old_view_msg_id
            )
    
    sent_msg = await send_post_media(
        message=callback.message,
        file_id=data["file_id"],
        media_type=data["media_type"],
        caption=data["caption"],
        reply_markup=data["markup"]
    )

    await state.update_data(opened_post_msg_id=sent_msg.message_id, opened_post_id=post_id)

    await callback.answer()

@router.callback_query(
        AdminPanel.post_queue_page, 
        F.data == AdminCB.CLOSE_POST
        )
async def view_post_close_btn_clicked(callback: CallbackQuery, state: FSMContext):      
    await callback.message.delete()

    await state.update_data(opened_post_msg_id=None)

    await callback.answer()

@router.message(
        StateFilter(AdminPanel.post_queue_page),
        F.photo | F.video | F.animation
        )
async def handle_media_content(message: Message, state: FSMContext):
    message_text, reply_markup = await window.get_unknown_command_window()
    await message.reply("Во время просмотра очереди нельзя загружать новые посты!", reply_markup=reply_markup)