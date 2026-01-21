from contextlib import suppress
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery

from bot.misc.states import AdminPanel
from bot.misc.callbacks import AddPostCB, AdminCB
from bot.misc.util import send_post_media, get_next_post_slot
from bot.database.requests import get_post
import bot.windows.admin as window
import bot.services.admin as service



router = Router()

@router.callback_query(
        AddPostCB.filter(),
        AdminPanel.post_queue_page
        )
async def add_post_from_queue_list(callback: CallbackQuery, state: FSMContext, callback_data: AddPostCB):
    # Close post view if opened
    state_data = await state.get_data()
    opened_post_id = state_data.get("opened_post_id")
    view_msg_id = state_data.get("opened_post_msg_id")

    if view_msg_id is not None:
        with suppress(TelegramBadRequest):
            await callback.message.bot.delete_message(
                chat_id=callback.message.chat.id,
                message_id=view_msg_id
            )
        await state.update_data(opened_post_msg_id=None, opened_post_id=None)

    day = callback_data.day
    month = callback_data.month
    year = callback_data.year
    hour = callback_data.hour
    minute = callback_data.minute
    date = datetime(year, month, day, hour, minute)

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Назад", callback_data=AdminCB.POST_QUEUE))

    await callback.message.edit_text(f"Добавление поста на {date.strftime('%d.%m.%Y %H:%M')}\n Ожидаю медиафайл...", reply_markup=builder.as_markup())

    await state.set_state(AdminPanel.add_post_for_date_page)
    await state.update_data(day=day, month=month, year=year, hour=hour, minute=minute, opened_post_id=None, opened_post_msg_id=None)
    await callback.answer()

@router.message(
        StateFilter(AdminPanel.add_post_for_date_page),
        F.photo | F.video | F.animation
        )
async def handle_media_content(message: Message, state: FSMContext, album: list[Message] = None ):
    state_data = await state.get_data()
    day = state_data.get("day")
    month = state_data.get("month")
    year = state_data.get("year")
    hour = state_data.get("hour")
    minute = state_data.get("minute")
    date = datetime(year, month, day, hour, minute)

    dt, caption = await get_next_post_slot(date - timedelta(seconds=1))
    
    post = await service.enqueue_messages_media_for_date(message, dt, caption)
    posts_args = [post]
    bad_statuses = []
    if album is not None and len(album) >= 2:
        bad_statuses = [{"status":"Недопустимо больше 1 медиафайла в сообщении"} for i in range(0, len(album)-1)]
    posts_args += bad_statuses
    message_text, reply_markup = await window.get_message_enqueue_answer(posts_args)
    await message.reply(message_text, reply_markup=reply_markup)
    if post["status"] == "OK":
        message_text, reply_markup = await window.get_post_queue_window(date)
        await state.set_state(AdminPanel.post_queue_page)
        list_message = await message.answer(message_text, reply_markup=reply_markup)
        await state.update_data(list_msg_id=list_message.message_id)


