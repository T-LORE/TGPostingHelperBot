import aiosqlite
from bot.misc.env_config_reader import settings

async def is_admin(user_id: int) -> bool:
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            "SELECT 1 FROM admins WHERE user_id = ?", 
            (user_id,)
        ) as cursor:
            return await cursor.fetchone() is not None