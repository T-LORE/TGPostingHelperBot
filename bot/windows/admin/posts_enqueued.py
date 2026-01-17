from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot.misc.callbacks import AdminCB

async def get_message_enqueue_answer(posts: list) -> tuple[str, InlineKeyboardMarkup]:
    message_text= ""
    every_post_message = ""
    added_count = 0
    for post in posts:
        if post["status"] == "OK":
           every_post_message += f"✅ ID поста: {post["post_id"]}\n"
           added_count += 1
        else:
            every_post_message += f"❌ Пост не добавлен, ошибка: {post["status"]}\n"
    
    if added_count == 0:
        message_text = (f"Ошибка, медиафайлы не были добавлены в очередь!\n\n")
    else:
        message_text = (f"Добавлено {added_count} постов в очередь!\n\n")
    
    message_text += every_post_message

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="Показать главную страницу",
        callback_data=AdminCB.RETURN_MAIN
    ))
    
    return message_text, builder.as_markup()