from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot.misc.callbacks import AdminCB, NavigationCB, DeletePostCB

from bot.database.requests import get_post


async def get_post_view_window(post_id: int, page: int) -> tuple[str, InlineKeyboardMarkup]:
    post_data = await get_post(post_id)
    if post_data is None:
        return None
    
    return {
        "caption": post_data["caption"],
        "file_id": post_data["file_id"],
        "media_type": post_data["media_type"],
        "publish_date": post_data["publish_date"],
        "markup": get_buttons_markup(post_id, page)
    } 

def get_buttons_markup(post_id: int, page: int = 1):
    builder = InlineKeyboardBuilder()
   
    back_btn = InlineKeyboardButton(
            text="Закрыть пост",
            callback_data=AdminCB.CLOSE_POST
        )
    delete_btn = InlineKeyboardButton(
            text="Удалить пост",
            callback_data=DeletePostCB(id=post_id, page=page, source="view").pack()
        )
    row = [back_btn, delete_btn]

    builder.row(*row)

    return builder.as_markup()