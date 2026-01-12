import aiosqlite
import sqlite3
import datetime

from bot.misc.env_config_reader import settings

async def is_admin(user_id: int) -> bool:
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            "SELECT 1 FROM admins WHERE user_id = ?", 
            (user_id,)
        ) as cursor:
            return await cursor.fetchone() is not None
        
async def add_to_queue(file_id: str, caption: str, media_type: str, publish_date: datetime):
    async with aiosqlite.connect(settings.database_path,
                                 detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) as db:
        async with db.execute(
            "INSERT INTO queue (file_id, caption, media_type, publish_date) VALUES (?, ?, ?, ?)", 
            (file_id, caption, media_type, publish_date)
        ) as cursor:
            post_id = cursor.lastrowid

        await db.commit()

        return post_id

async def get_queue_count():
    async with aiosqlite.connect(settings.database_path,
                                 detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM queue"
        ) as cursor:
            count = await cursor.fetchone()
            return count[0]

async def get_latest_post():
    async with aiosqlite.connect(settings.database_path,
                                 detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) as db:
        db.row_factory = sqlite3.Row

        async with db.execute(
            "SELECT * FROM queue ORDER BY publish_date DESC LIMIT 1"
        ) as cursor:
            post = await cursor.fetchone()
            return post
        
async def get_earliest_post():
    async with aiosqlite.connect(settings.database_path,
                                 detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) as db:
        db.row_factory = sqlite3.Row

        async with db.execute(
            "SELECT * FROM queue ORDER BY publish_date ASC LIMIT 1"
        ) as cursor:
            post = await cursor.fetchone()
            return post

async def delete_all_posts():
    async with aiosqlite.connect(settings.database_path,
                                 detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) as db:
        await db.execute("DELETE FROM queue")

        await db.commit()