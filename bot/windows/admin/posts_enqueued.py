from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

async def get_message_enqueue_answer(added_posts_id: list[int]) -> tuple[str, InlineKeyboardMarkup]:
    added_count = len(added_posts_id)
    
    if added_count == 0:
        message_text = (f"Ошибка, медиафайлы не были добавлены в очередь!")
    else:
        message_text = (f"✅ Добавлено {added_count} постов в очередь!\n\n")
        for post_id in added_posts_id:
            message_text += f"ID поста: {post_id}\n"

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="Показать главную страницу",
        callback_data="return_to_main_page"
    ))
    
    return message_text, builder.as_markup()