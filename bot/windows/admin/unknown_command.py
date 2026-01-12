from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

async def get_unknown_command_window() -> tuple[str, InlineKeyboardMarkup]:
    message_text = (f"""
    Неизвестая команда!"""
    )

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="Вернуться на главную",
        callback_data="return_to_main_page"
    ))
    
    return message_text, builder.as_markup()