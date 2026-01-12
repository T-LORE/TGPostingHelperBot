from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot.misc.callbacks import AdminCB

async def get_unknown_command_window() -> tuple[str, InlineKeyboardMarkup]:
    message_text = (f"""
    Неизвестая команда!"""
    )

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="Вернуться на главную",
        callback_data=AdminCB.RETURN_MAIN
    ))
    
    return message_text, builder.as_markup()