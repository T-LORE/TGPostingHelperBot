import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import asyncio 

from aiogram.types import Message
from aiogram.types import Message, InlineKeyboardMarkup

from bot.misc.config import config

processing_lock = asyncio.Lock()

def create_file_if_not_exist(path):
    if os.path.isfile(path):
        return False
    
    database_dir = os.path.dirname(path)
    
    if not os.path.exists(database_dir):
        os.makedirs(database_dir)

    with open(path, 'a'):
        os.utime(path, None)

    return True
  
async def get_next_post_slot(last_date: datetime | None):
    slots = []
    for slot in config.post_timestamps:
        t = datetime.strptime(slot.time.strip(), "%H:%M").time()
        slots.append({"time": t, "caption": slot.caption})
    
    slots.sort(key=lambda x: x["time"])

    if not last_date:
        last_date = datetime.now()

    current_time = last_date.time()

    for slot in slots:
        if slot["time"] > current_time:
            next_dt = datetime.combine(last_date.date(), slot["time"])
            return next_dt, slot["caption"]

    first_slot = slots[0]
    next_day = last_date.date() + timedelta(days=1)
    next_dt = datetime.combine(next_day, first_slot["time"])
    
    return next_dt, first_slot["caption"]

def convert_timezone(date: datetime) -> datetime:
    target_tz = ZoneInfo(config.timezone)
    
    return date.astimezone(target_tz)

async def send_post_media(message: Message, file_id: str, media_type: str, caption: str, reply_markup: InlineKeyboardMarkup = None) -> Message | None:
    if media_type == "photo":
        return await message.answer_photo(photo=file_id, caption=caption, reply_markup=reply_markup)
    elif media_type == "video":
        return await message.answer_video(video=file_id, caption=caption, reply_markup=reply_markup)
    elif media_type == "animation":
        return await message.answer_animation(animation=file_id, caption=caption, reply_markup=reply_markup)
    else:
        raise Exception("Invalid media type")
    
def parse_posts_from_message(message: Message) -> list[dict]:
    text = message.text or message.caption or ""
    lines = text.split('\n')
    
    posts = []
    
    id_pattern = re.compile(r"#(\d+)")
    
    for line in lines:
        match = id_pattern.search(line)
        
        if match:
            post_id = int(match.group(1))
            
            if "✅" in line:
                status = "OK"
            elif "🗑" in line:
                status = "DELETED"
            else:
                status = "UNKNOWN"

            posts.append({
                "post_id": post_id,
                "status": status
            })
            
        elif "❌" in line:
            error_text = line.split(":", 1)[-1].strip() if ":" in line else "Unknown error"
            posts.append({
                "post_id": None,
                "status": error_text
            })
            
    return posts