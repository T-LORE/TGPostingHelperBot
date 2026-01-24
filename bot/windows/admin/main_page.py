from datetime import datetime, timedelta
import textwrap

from babel.dates import format_date
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.services.schedule_poster import resolve_id_to_info
from bot.misc.callbacks import AdminCB
from bot.database.requests import get_queue_count, get_not_published_posts
from bot.misc.config import config, env
from bot.misc.util import get_next_free_slots
from bot.services.schedule_poster import get_scheduled_messages_count

FREE_SLOTS_AMOUNT = 3
FREE_SLOTS_DAYS_CHECK = 30

_cache = {
    "admin_link": None,
    "channel_link": None
}

async def get_main_menu_window() -> tuple[str, InlineKeyboardMarkup]:
    not_published_posts = await get_not_published_posts()

    expired_posts = get_expired_posts(not_published_posts)
    expired_message = f"⛔️ ПРОСРОЧЕНО: {len(expired_posts)}\n" if len(expired_posts) > 0 else ""

    order_failure_posts = get_tg_order_failure_posts(not_published_posts)
    order_failure_message = f"⛔️ Сбой порядка в отложке TG\n(Нужно обновить отложку)\n" if len(order_failure_posts) > 0 else ""
    
    actual_post_in_tg_count = await get_scheduled_messages_count()
    db_post_in_tg = get_posts_in_tg_schedule(not_published_posts)
    db_post_in_tg_count = len(db_post_in_tg)
    tg_desync_error = f"⚠️ Возможная ошибка - кол-во постов в отложке телеграмма не совпадает с информацией очереди: {actual_post_in_tg_count}/{db_post_in_tg_count}\n" if db_post_in_tg_count != actual_post_in_tg_count else ""

    warning_message = ""
    if len(expired_posts) > 0 or len(order_failure_posts) > 0 or db_post_in_tg_count != actual_post_in_tg_count:
        warning_message = f"🔴 ВНИМАНИЕ! 🔴\n\n{expired_message}{order_failure_message}{tg_desync_error}"

    admin_info = _cache["admin_link"] if _cache["admin_link"] is not None else await resolve_id_to_info(env.root_admin_id)
    channel_info = _cache["channel_link"] if _cache["channel_link"] is not None else await resolve_id_to_info(env.channel_id)
    _cache["admin_link"] = admin_info
    _cache["channel_link"] = channel_info

    current_tg_load = get_tg_current_tg_load(not_published_posts)
    progress_bar = get_progress_bar(current_tg_load, config.max_tg_buffer_size, 10)
    last_post_str = "Нет запланированных"
    if len(not_published_posts) > 0:
        dt = not_published_posts[-1]["publish_date"]
        last_post_str = get_post_date_text(dt)

    next_post = get_next_post_date_text(not_published_posts)

    free_slots_text = await get_next_free_slots_text(FREE_SLOTS_AMOUNT)

    message_text = (
f"""📡 <b>Панель управления</b>
👤 <b>Админ-постер:</b> 
{admin_info['link']}
📢 <b>Канал:</b> 
{channel_info['link']}

📊 <b>Очередь бота:</b>
📦 В базе: {len(not_published_posts)} шт.
🗓 В отложке: {db_post_in_tg_count} шт.

🏁 <b>Последний пост:</b> 
{last_post_str}
<i>(Точка отсчета автопостинга)</i>

⏳ <b>Следующий пост:</b>
{next_post}

📡 <b>Буфер Telegram:</b>
{progress_bar}
<i>(Заполнено {current_tg_load} из {config.max_tg_buffer_size} мест)</i>

⚠️ <b>Ближайшие свободные места:</b>
{free_slots_text} {warning_message}
-----------------------------
<i>(Жду файлы для загрузки...)</i>
"""
    )
    message_text = textwrap.dedent(message_text)

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить", callback_data=AdminCB.UPDATE),
        InlineKeyboardButton(text="Удалить всё", callback_data=AdminCB.DELETE_ALL_CONFIRM)
        )
    builder.row(InlineKeyboardButton(text="Просмотр постов", callback_data=AdminCB.POST_QUEUE))
    builder.row(InlineKeyboardButton(text="Обновить отложку телеграмма", callback_data=AdminCB.UPDATE_TG_SCHEDULE))

    
    return message_text, builder.as_markup()

def get_expired_posts(posts):
    expired_posts = []
    for post in posts:
        if post["tg_message_id"] is None and post["publish_date"] <= datetime.now():
            expired_posts.append(post)

    return expired_posts

def get_posts_in_tg_schedule(not_published_posts):
    future_posts = [p for p in not_published_posts if p["publish_date"] > datetime.now()]
    posts_in_schedule = []

    for post in future_posts:
        if post["tg_message_id"] is not None:
            posts_in_schedule.append(post)

    return posts_in_schedule

def get_tg_order_failure_posts(not_published_posts):
    future_posts = [p for p in not_published_posts if p["publish_date"] > datetime.now()]
    order_failure_posts = []

    is_in_tg_schedule = False

    for post in reversed(future_posts):
        if post["tg_message_id"] is not None:
            is_in_tg_schedule = True
        elif is_in_tg_schedule == True:
            order_failure_posts.append(post)

    return order_failure_posts

def get_admin_poster_name():
    return f"{env.root_admin_id}"

def get_group_name():
    return f"{env.channel_id}"

def get_tg_current_tg_load(not_expired_posts):
    current_tg_load = 0
    for post in not_expired_posts:
        if post["tg_message_id"] is not None and post["publish_date"] > datetime.now():
            current_tg_load += 1

    return current_tg_load

def get_progress_bar(current: int, total: int = 10, length: int = 10) -> str:
    if total == 0:
        empty_bar = '□' * length
        return f"<code>[{empty_bar}]</code> <b>0%</b>"

    percent = (current / total) * 100
    
    filled_len = int(length * (current / total))
    filled_len = min(length, max(0, filled_len))
    
    empty_len = length - filled_len

    bar = '■' * filled_len + '□' * empty_len
    
    return f"[{bar}] <b>{round(percent)}%</b>"

def get_next_post_date_text(not_published_posts):
    future_posts = [p for p in not_published_posts if p["publish_date"] > datetime.now()]

    if not future_posts:
        return "Нет запланированных"

    next_post = future_posts[0]
    dt = next_post["publish_date"]

    post_text = get_post_date_text(dt)
    
    timer_str = get_time_until_str(dt)

    return f"{post_text}\n<i>{timer_str}</i>"

def get_post_date_text(dt):
    day_str = get_human_date_str(dt)
    
    time_str = dt.strftime("%H:%M")
    
    return f"<b>{day_str} {time_str}</b>"

def get_time_until_str(dt: datetime) -> str:
    now = datetime.now()
    diff = dt - now
    
    if diff.total_seconds() < 0:
        return "(сейчас)"
    
    total_seconds = int(diff.total_seconds())
    days = total_seconds // 86400
    remaining_seconds = total_seconds % 86400
    hours = remaining_seconds // 3600
    minutes = (remaining_seconds % 3600) // 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}д")
    if hours > 0 or days > 0:
        parts.append(f"{hours}ч")
    
    parts.append(f"{minutes}м")
    
    time_str = " ".join(parts)
    return f"(через {time_str})"

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
        return format_date(dt, "d MMM", locale='ru').title()

async def get_next_free_slots_text(n: int):
    free_slots = await get_next_free_slots(n, 30, datetime.now())
    
    if len(free_slots) == 0:
        return f"В ближайшие {FREE_SLOTS_DAYS_CHECK} дней свободных слотов нет"
    
    message_text = ""
    for slot in free_slots:
        if slot.date() == datetime.now().date():
            message_text += "🔴"
        elif slot.date() == datetime.now().date() + timedelta(days=1):
            message_text += "🟡"
        else:
            message_text += "⚪️"

        message_text += f" {get_post_date_text(slot)}\n"
    
    return message_text

    