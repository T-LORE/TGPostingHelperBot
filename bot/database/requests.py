import aiosqlite
import sqlite3
import datetime
from datetime import timedelta

from bot.misc.config import env

db_path = env.database_path

async def is_admin(user_id: int) -> bool:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT 1 FROM admins WHERE user_id = ?", 
            (user_id,)
        ) as cursor:
            return await cursor.fetchone() is not None
        
async def add_to_queue(file_id: str, caption: str, media_type: str, publish_date: datetime):
    async with aiosqlite.connect(db_path,
                                 detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) as db:
        async with db.execute(
            "INSERT INTO queue (file_id, caption, media_type, publish_date) VALUES (?, ?, ?, ?)", 
            (file_id, caption, media_type, publish_date)
        ) as cursor:
            post_id = cursor.lastrowid

        await db.commit()

        return post_id

async def get_queue_count():
    async with aiosqlite.connect(db_path,
                                 detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM queue"
        ) as cursor:
            count = await cursor.fetchone()
            return count[0]

async def delete_all_posts():
    async with aiosqlite.connect(db_path,
                                 detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) as db:
        await db.execute("DELETE FROM queue")

        await db.commit()

async def delete_post(post_id: int):
    async with aiosqlite.connect(db_path,
                                 detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) as db:
        await db.execute("DELETE FROM queue WHERE id = ?", (post_id,))

        await db.commit()

async def get_post(post_id: int):
    async with aiosqlite.connect(db_path,
                                 detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) as db:
        db.row_factory = sqlite3.Row
        async with db.execute(
            "SELECT * FROM queue WHERE id = ?", 
        (post_id,)) as cursor:
            result = await cursor.fetchone()
            return None if result is None else result

async def update_post_tg_id(post_id: int, tg_message_id: int):
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE queue SET tg_message_id = ? WHERE id = ?",
            (tg_message_id, post_id)
        )
        await db.commit()

async def get_not_tg_scheduled_posts(limit: int = 10):
    async with aiosqlite.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) as db:
        db.row_factory = sqlite3.Row
        async with db.execute(
            "SELECT * FROM queue WHERE tg_message_id IS NULL ORDER BY publish_date ASC LIMIT ?",
            (limit,)
        ) as cursor:
            return await cursor.fetchall()
        
async def get_tg_scheduled_posts():
    now = datetime.datetime.now() + datetime.timedelta(minutes=5)
    async with aiosqlite.connect(db_path,
                                 detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) as db:
        db.row_factory = sqlite3.Row
        async with db.execute(
            "SELECT * FROM queue WHERE tg_message_id IS NOT NULL AND publish_date > ? ORDER BY publish_date ASC",
            (now,) 
        ) as cursor:
            result = await cursor.fetchall()
            return None if result is None else result
        
async def get_not_published_posts():
    now = datetime.datetime.now() + datetime.timedelta(minutes=5)
    async with aiosqlite.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) as db:
        db.row_factory = sqlite3.Row
        async with db.execute(
            "SELECT * FROM queue WHERE publish_date > ? OR (publish_date <= ? AND tg_message_id IS NULL) ORDER BY publish_date ASC",
            (now, now)
        ) as cursor:
            return await cursor.fetchall()
        
async def get_post_by_day(day: datetime):
    start_of_day = day.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    async with aiosqlite.connect(db_path,
                                 detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) as db:
        db.row_factory = sqlite3.Row
        
        async with db.execute(
            "SELECT * FROM queue WHERE publish_date >= ? AND publish_date < ? ORDER BY publish_date ASC", 
            (start_of_day, end_of_day)
        ) as cursor:
            return await cursor.fetchall()
        
async def add_admin_to_db(user_id: int, role: str) -> bool:
    async with aiosqlite.connect(db_path,
                                 detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) as db:
        async with db.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,)) as cursor:
            if await cursor.fetchone():
                return False
        
        await db.execute("INSERT INTO admins (user_id, role) VALUES (?, ?)", (user_id, role))
        await db.commit()
        return True

async def remove_admin_from_db(user_id: int) -> bool:
    async with aiosqlite.connect(db_path,
                                 detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) as db:
        async with db.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,)) as cursor:
            if not await cursor.fetchone():
                return False
                
        await db.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        await db.commit()
        return True
    
async def get_all_admins() -> list[int]:
    async with aiosqlite.connect(db_path,
                                 detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) as db:
        async with db.execute("SELECT user_id FROM admins") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]