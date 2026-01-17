import aiosqlite
import logging

from bot.misc.env_config_reader import settings
from bot.misc.util import create_file_if_not_exist

logger = logging.getLogger(__name__)
async def start_db():
    
    if create_file_if_not_exist(settings.database_path):
        logger.warning(f"New database file \"{settings.database_path}\" was created!")
    else:
        logger.warning(f"Use existing database: \"{settings.database_path}\"")

    async with aiosqlite.connect(settings.database_path) as db:
   
        await db.execute("""
            CREATE TABLE IF NOT EXISTS queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT NOT NULL,
                caption TEXT,
                media_type TEXT DEFAULT 'photo',
                publish_date TIMESTAMP,
                tg_message_id INTEGER DEFAULT NULL,
                status TEXT DEFAULT 'pending',
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
