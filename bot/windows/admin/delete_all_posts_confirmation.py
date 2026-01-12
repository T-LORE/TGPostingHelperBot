from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot.misc.callbacks import AdminCB

async def get_delete_all_posts_confirmation() -> tuple[str, InlineKeyboardMarkup]:
    message_text = (f"""Подтвердите удаление всех постов.""")

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="Да",
        callback_data=AdminCB.DELETE_ALL
    ))
    builder.add(InlineKeyboardButton(
        text="Нет",
        callback_data=AdminCB.RETURN_MAIN_EDIT
    ))
    
    return message_text, builder.as_markup()