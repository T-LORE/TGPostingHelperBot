from aiogram import Router, F
from aiogram.types import Message

import bot.windows.admin as window

router = Router()

@router.message()
async def unknown_command(message: Message):
    message_text, reply_markup = await window.get_unknown_command_window()
    await message.reply(message_text,
    reply_markup=reply_markup)
