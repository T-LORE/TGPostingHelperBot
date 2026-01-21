import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import asyncio 

from aiogram.types import Message
from aiogram.types import Message, InlineKeyboardMarkup

from bot.misc.config import config
from bot.database.requests import get_post_by_day

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

async def get_next_free_slots(limit: int = 3, next_days: int = 30, start_datetime: datetime = datetime.now()) -> list[datetime]:
    found_slots = []
    
    schedule_times = sorted([
        datetime.strptime(slot.time, "%H:%M").time() 
        for slot in config.post_timestamps
    ])
    
    if not schedule_times:
        return []

    check_date = start_datetime.combine(start_datetime, datetime.min.time())
    
    for _ in range(next_days): 
        day = check_date
        
        posts = await get_post_by_day(day)
        post_dates = [post["publish_date"] for post in posts]

        for time_obj in schedule_times:
            slot_dt = datetime.combine(check_date, time_obj)
            
            if slot_dt <= datetime.now():
                continue
            
            if slot_dt not in post_dates:
                found_slots.append(slot_dt)
                
                if len(found_slots) >= limit:
                    return found_slots
        
        check_date += timedelta(days=1)

    return found_slots
