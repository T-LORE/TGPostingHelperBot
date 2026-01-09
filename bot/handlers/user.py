from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters.command import Command

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Hello world!")

