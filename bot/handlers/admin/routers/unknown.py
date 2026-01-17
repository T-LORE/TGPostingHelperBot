from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

import bot.windows.admin as window

router = Router()

@router.message()
async def unknown_command(message: Message):
    message_text, reply_markup = await window.get_unknown_command_window()
    await message.reply(message_text,
    reply_markup=reply_markup)



@router.callback_query()
async def unknown_callback(callback: CallbackQuery):
    await callback.answer("Эта кнопка больше не активна или действие неизвестно. Возможно старое сообщение или бот был перезапущен.", show_alert=True)