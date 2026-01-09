import aiosqlite
from bot.misc.env_config_reader import settings
from bot.misc.util import create_file_if_not_exist


async def start_db():
    if create_file_if_not_exist(settings.database_path):
        print(f"INFO:New database file \"{settings.database_path}\" was created!")
    else:
        print(f"INFO:Use existing database: \"{settings.database_path}\"")

    async with aiosqlite.connect(settings.database_path) as db:
   
        await db.execute("""
            CREATE TABLE IF NOT EXISTS queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT NOT NULL,
                caption TEXT,
                media_type TEXT DEFAULT 'photo',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY
            )
        """)
        
        await db.execute(
            "INSERT OR IGNORE INTO admins (user_id) VALUES (?);",
            (settings.root_admin_id,)
        )

        await db.commit()
