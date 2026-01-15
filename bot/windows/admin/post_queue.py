import textwrap

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot.misc.callbacks import AdminCB, NavigationCB, DeletePostCB, ViewPostCB

from bot.database.requests import get_queue_count, get_earliest_posts

POSTS_ON_PAGE = 10

async def get_post_queue_window(page_number: int) -> tuple[str, InlineKeyboardMarkup]:
    queue_count = await get_queue_count()
    
    if queue_count == 0:
        return "Список пуст.", InlineKeyboardBuilder().add(InlineKeyboardButton(text="Назад", callback_data=AdminCB.RETURN_MAIN_EDIT)).as_markup()
    
    page_count = (queue_count + POSTS_ON_PAGE - 1) // POSTS_ON_PAGE
    
    if page_number > page_count: 
        page_number = page_count
    if page_number < 1: 
        page_number = 1
    
    start_post = (page_number - 1) * POSTS_ON_PAGE
    posts_queue = await get_earliest_posts(start_post, POSTS_ON_PAGE)

    post_page_text = ""
    for number, post in enumerate(posts_queue, start=start_post + 1):
        post_page_text += f"{number}. {create_post_string(post['id'], post['publish_date'])}\n"
    
    message_text = (f"""
Список (Стр. {page_number}/{page_count})
-------------------
{post_page_text}
""")

    builder = InlineKeyboardBuilder()
    for index, post in enumerate(posts_queue, start=start_post + 1):
        post_buttons_row = []
        delete_btn = InlineKeyboardButton(
            text=f"🗑 {index}",
            callback_data=DeletePostCB(id=post['id'], page=page_number).pack()
        )
        view_btn = InlineKeyboardButton(
            text=f"🔎 {index}",
            callback_data=ViewPostCB(id=post['id'], page=page_number).pack()
        )
        post_buttons_row = [delete_btn, view_btn]
        builder.row(*post_buttons_row, width=5)
    
    page_nav_row = []
    previous_page_btn = InlineKeyboardButton(
            text="⬅️",
            callback_data=NavigationCB(page=page_number - 1).pack()
        )
    next_page_btn = InlineKeyboardButton(
            text="➡️",
            callback_data=NavigationCB(page=page_number + 1).pack()
        )
    menu_btn = InlineKeyboardButton(
        text="В меню",
        callback_data=AdminCB.RETURN_MAIN_EDIT
    )
    if page_number > 1:
        page_nav_row.append(previous_page_btn)
    if page_number < page_count:
        page_nav_row.append(next_page_btn)

    builder.row(*page_nav_row)
    builder.row(*[menu_btn])
    
    return message_text, builder.as_markup()

def create_post_string(post_id: int, publish_date: str) -> str:
    date_str = publish_date.strftime("Дата: %d.%m Время: %H:%M")
    return f"#{post_id} {date_str}"