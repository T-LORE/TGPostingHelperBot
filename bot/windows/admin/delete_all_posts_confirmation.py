from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

async def get_delete_all_posts_confirmation() -> tuple[str, InlineKeyboardMarkup]:
    message_text = (f"""Подтвердите удаление всех постов.""")

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="Да",
        callback_data="delete_all_posts"
    ))
    builder.add(InlineKeyboardButton(
        text="Нет",
        callback_data="return_to_main_page_with_edit"
    ))
    
    return message_text, builder.as_markup()