import textwrap
import logging
from datetime import datetime, timedelta

from babel.dates import format_date, format_datetime, format_time
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot.misc.callbacks import AdminCB, NavigationCB, DeletePostCB, ViewPostCB, DateViewCB, AddPostCB

from bot.database.requests import get_queue_count, get_post_by_day, get_not_published_posts
from bot.misc.config import config

logger = logging.getLogger(__name__)

async def get_post_queue_window(date: datetime) -> tuple[str, InlineKeyboardMarkup]:
    date = datetime.combine(date, datetime.min.time())
    
    not_published_posts = await get_not_published_posts()
    post_at_date = await get_post_by_day(date)
    
    page_count = count_pages(not_published_posts)
    current_page = get_page_for_date(date, not_published_posts)

    if page_count == 0:
        page_count = 1
        current_page = 1
        date = datetime.now()

    # 🗓19 Января 2026 (Понедельник)
    day = date.day
    month = format_date(date.date(), "MMMM", locale='ru').capitalize()
    year = date.year
    weekday = format_date(date.date(), "EEEE", locale='ru').capitalize()
    date_text = f"🗓<b>{day} {month} {year}</b> ({weekday})"

    # 📖Стр. 1 из 5 (Сегодня)
    day_representation = get_human_date_str(date)
    day_representation = f"({day_representation})" if day_representation is not None else ""
    page_text = f"📖<i>Стр. {current_page} из {page_count}</i> {day_representation}"

    tables = get_tables_str(date, post_at_date)
    message_text = f"{date_text}\n{page_text}\n\n{tables}"

    buttons = get_buttons(date, not_published_posts, post_at_date)
    
    return message_text, buttons 

def get_post_queue_window_start():
    return get_post_queue_window(datetime.now().date())

def get_buttons(target_date, not_published_posts, target_posts):
    builder = InlineKeyboardBuilder()

    nav_builder = get_navigation_builder(target_date, not_published_posts)
    
    timestamps_posts, off_schedule_posts = sort_posts_by_timestamps(target_posts)
    timestamp_posts_builder = get_builder_for_timestamps_posts(timestamps_posts, target_date)
    off_schedule_posts_builder = get_builder_for_off_scheduled_posts(off_schedule_posts, target_date)
    
    menu_btn = InlineKeyboardButton(
        text="В меню",
        callback_data=AdminCB.RETURN_MAIN_EDIT
    )

    # off_schedule_empty_btn = InlineKeyboardButton(
    #         text="─ ⚡️ Вне графика ⚡️ ─", 
    #         callback_data="ignore"
    #     )

    builder.attach(timestamp_posts_builder)
    # if len(off_schedule_posts) > 0:
    #     builder.row(off_schedule_empty_btn)
    builder.attach(off_schedule_posts_builder)
    builder.attach(nav_builder)
    builder.row(menu_btn)

    return builder.as_markup()

def get_navigation_builder(target_date, not_published_posts):
    builder = InlineKeyboardBuilder()
    target_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    next_day = target_date + timedelta(days=1)
    previous_day = target_date - timedelta(days=1)
    earliest_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    latest_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    if len(not_published_posts) > 0:
        earliest_date = not_published_posts[0]["publish_date"].replace(hour=0, minute=0, second=0, microsecond=0)
        latest_date = not_published_posts[-1]["publish_date"].replace(hour=0, minute=0, second=0, microsecond=0)

    if earliest_date > datetime.now():
        earliest_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if latest_date < datetime.now():
        latest_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    buttons = []
    if target_date > earliest_date:
        buttons.append(InlineKeyboardButton(
            text="⬅️",
            callback_data=DateViewCB(
                        day=previous_day.day,
                        month=previous_day.month,
                        year=previous_day.year
                    ).pack()
                )
            )
    if target_date < latest_date:
        buttons.append(InlineKeyboardButton(
            text="➡️",
            callback_data=DateViewCB(
                        day=next_day.day,
                        month=next_day.month,
                        year=next_day.year
                    ).pack()
                )
            )
    builder.row(*buttons)
    return builder

def get_builder_for_timestamps_posts(posts, target_date: datetime):
    builder = InlineKeyboardBuilder()
    for timestamp in config.post_timestamps:
        timestamp = datetime.strptime(timestamp.time.strip(), "%H:%M").time()
        timestamp = datetime.combine(target_date.date(), timestamp)

        find_post = [post for post in posts if post["publish_date"].replace(second=0, microsecond=0) == timestamp]
        status = determine_post_status(timestamp, find_post[0] if len(find_post) >= 1 else None)
        btn = create_post_button(status=status, post_id=find_post[0]["id"] if len(find_post) >= 1 else None, publish_date=timestamp)
        if len(btn) > 0:
            builder.row(*btn)
    return builder

def get_builder_for_off_scheduled_posts(posts, target_date: datetime):
    builder = InlineKeyboardBuilder()
    for post in posts:
        status = determine_post_status(target_date, post)
        btn = create_post_button(status=status, post_id=post["id"], publish_date=post["publish_date"])
        if len(btn) > 0:
            builder.row(*btn)
    return builder 

def get_human_date_str(dt: datetime) -> str:
    now_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    target_date = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    
    delta_days = (target_date - now_date).days
    
    if delta_days == 0:
        return "Сегодня"
    elif delta_days == 1:
        return "Завтра"
    elif delta_days == 2:
        return "Послезавтра"
    elif delta_days == -1:
        return "Вчера"
    elif delta_days == -2:
        return "Позавчера"
    else:
        return None

def count_pages(not_published_posts):
    if len(not_published_posts) == 0:
        return 1
    
    earliest_post = not_published_posts[0]["publish_date"].replace(hour=0, minute=0, second=0, microsecond=0)
    latest_post = not_published_posts[-1]["publish_date"].replace(hour=0, minute=0, second=0, microsecond=0)

    if earliest_post > datetime.now():
        earliest_post = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if latest_post < datetime.now():
        latest_post = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    days = (latest_post - earliest_post).days
    return days + 1

def get_page_for_date(target_date: datetime, not_published_posts):
    if len(not_published_posts) == 0:
        return 1
    
    earliest_post = not_published_posts[0]["publish_date"].replace(hour=0, minute=0, second=0, microsecond=0)
    latest_post = not_published_posts[-1]["publish_date"].replace(hour=0, minute=0, second=0, microsecond=0)

    if earliest_post > datetime.now():
        earliest_post = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if latest_post < datetime.now():
        latest_post = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    sorted_days = [earliest_post + timedelta(days=x) for x in range((latest_post - earliest_post).days + 1)]

    if target_date not in sorted_days:
        if target_date > sorted_days[-1]:
            target_date = sorted_days[-1]
        elif target_date < sorted_days[0]:
            target_date = sorted_days[0]

    page = sorted_days.index(target_date) + 1
    return page

def get_tables_str(target_date: datetime, posts):
    timestamps_posts, off_schedule_posts = sort_posts_by_timestamps(posts)

    timestamp_table = create_timestamp_table(timestamps_posts, target_date)
    off_schedule_table = create_off_schedule_table(off_schedule_posts, target_date)
    table_str = f"<b>Основное расписание:</b>\n{timestamp_table}"
    if len(off_schedule_posts) > 0:
        table_str += f"\n\n📌<b>Вне графика:</b>\n{off_schedule_table}"
    return table_str

def sort_posts_by_timestamps(posts):
    posts_copy = posts.copy()

    timestamps_posts = []
    off_schedule_posts = []

    timestamps = [datetime.strptime(stamp.time.strip(), "%H:%M").time() for stamp in config.post_timestamps]

    for timestamp in timestamps:
        find_post = [post for post in posts_copy if post["publish_date"].time().replace(second=0, microsecond=0) == timestamp]
        if len(find_post) >= 2:
            logger.warning(f"Found many posts for timestamp {timestamp} ({[post['id'] for post in find_post]}).")
        if len(find_post) >= 1:
            timestamps_posts.append(find_post[0])
            posts_copy.remove(find_post[0])
    
    off_schedule_posts += posts_copy

    return timestamps_posts, off_schedule_posts

def create_timestamp_table(posts, target_date: datetime):
    table = ""
    for timestamp in config.post_timestamps:
        timestamp = datetime.strptime(timestamp.time.strip(), "%H:%M").time()
        timestamp = datetime.combine(target_date.date(), timestamp)

        find_post = [post for post in posts if post["publish_date"].replace(second=0, microsecond=0) == timestamp]
        status = determine_post_status(timestamp, find_post[0] if len(find_post) >= 1 else None)

        table += create_table_row(timestamp, find_post[0]["id"] if len(find_post) >= 1 else None, status)

    return table

def create_off_schedule_table(posts, target_date: datetime):
    table = ""
    for post in posts:
        status = determine_post_status(target_date, post)
        table += create_table_row(post["publish_date"], post["id"], status)
    
    return table


def determine_post_status(target_date: datetime, post = None):
    status = "unknown"
    if post == None:
        status = "free" if datetime.now() < target_date else status
        status = "missed" if datetime.now() >= target_date else status
        return status
    
    status = "expired" if post["publish_date"] <= datetime.now() and post["tg_message_id"] is None else status
    status = "tg_hold" if post["tg_message_id"] is not None and post["publish_date"] > datetime.now() else status
    status = "posted" if post["tg_message_id"] is not None and post["publish_date"] <= datetime.now() else status
    status = "db_hold" if post["tg_message_id"] is None and post["publish_date"] > datetime.now() else status

    return status


def create_table_row(time: datetime, post_id: int, status: str):
    STATUS_MAP = {
    "expired":   {"icon": "💔", "text": "Просрочен"},
    "tg_hold":   {"icon": "✈️", "text": "В отложке"},
    "posted":    {"icon": "✅", "text": "Выложен"},
    "db_hold":   {"icon": "📦", "text": "Создан"},
    "free":      {"icon": "❌", "text": "Свободно"},
    "missed":    {"icon": "⚪️", "text": "Пусто"},
    }
    
    if post_id is None:
        post_id = normalize_str("----", 4)
    else:
        post_id = normalize_str(f"#{str(post_id)}", 4)

    status_data = STATUS_MAP[status] if status in STATUS_MAP else {"icon": "❓", "text": "Неизвестно"}
    
    time = time.strftime("%H:%M")
    row = f"<code>{time} </code>|<code> {post_id} </code>| {status_data['icon']} {status_data['text']}\n"

    return row

def create_post_button(status, post_id : int = None, publish_date : datetime = None):
    if status == "expired":
        return [InlineKeyboardButton(
            text=f"🗑", 
            callback_data=DeletePostCB(
                id=post_id, 
                source="list", 
                page=-1).pack())]
    
    elif status == "free":
        return [InlineKeyboardButton(
            text=f"➕ Занять слот {publish_date.strftime('%H:%M')}", 
            callback_data=AddPostCB(
                day=publish_date.day,
                month=publish_date.month,
                year=publish_date.year,
                hour=publish_date.hour,
                minute=publish_date.minute
            ).pack())]
    
    elif status == "tg_hold" or status == "db_hold":
        return [
            InlineKeyboardButton(
                text=f"{publish_date.strftime('%H:%M')}: 🔎", 
                callback_data=ViewPostCB(
                    id=post_id, 
                    page=-1).pack()),
            InlineKeyboardButton(
                text=f"🗑", 
                callback_data=DeletePostCB(
                    id=post_id,
                    page=-1,
                    source="list"
            ).pack())]
    
    elif status == "posted":
        return [
            InlineKeyboardButton(
                text=f"{publish_date.strftime('%H:%M')}: 🔎", 
                callback_data=ViewPostCB(
                    id=post_id, 
                    page=-1).pack())]
    
    else:
        return []



def normalize_str(text, width = 10):
    text = str(text)
    current_len = len(text)
    
    if current_len > width:
        if width <= 3:
            return text[:width]
        
        side_len = (width - 3) // 2
        left_part = text[:side_len]
        right_part = text[-(width - 3 - side_len):]
        
        return f"{left_part}...{right_part}"
    
    else:
        return text.center(width)