from aiogram.filters import BaseFilter
from aiogram.types import Message
from bot.database.requests import is_admin

class IsAdmin(BaseFilter):
    # That's not good((
    async def __call__(self, message: Message) -> bool:
        if not message.from_user:
            return False
            
        return await is_admin(message.from_user.id)