from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot.misc.callbacks import AdminCB

from bot.database.requests import get_queue_count, get_earliest_posts

async def get_main_menu_window() -> tuple[str, InlineKeyboardMarkup]:
    queue_count = await get_queue_count()
    earliest_posts = await get_earliest_posts(start_post=1, posts_amount=1)
    
    if earliest_posts is not None and len(earliest_posts) > 0:
        next_date = earliest_posts[0]["publish_date"]
    else:
        next_date = "Нет запланированных"

    message_text = (f"""
    ГЛАВНОЕ МЕНЮ / СТАТИСТИКА
    -------------------
    Админ: user_id - role_id
    Управляемая группа: group_id
                         
    В очереди: {queue_count} поста
    След. пост: {next_date}
    -------------------
    (Жду файлы для загрузки...)"""
    )

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="🔄 Обновить",
        callback_data=AdminCB.UPDATE
    ))
    builder.add(InlineKeyboardButton(
        text="Удалить всё",
        callback_data=AdminCB.DELETE_ALL_CONFIRM
    ))
    builder.add(InlineKeyboardButton(
        text="Просмотр постов",
        callback_data=AdminCB.POST_QUEUE
    ))
    
    return message_text, builder.as_markup()