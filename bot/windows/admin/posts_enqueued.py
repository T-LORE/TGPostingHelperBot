from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot.misc.callbacks import AdminCB, DeletePostCB

async def get_message_enqueue_answer(posts: list) -> tuple[str, InlineKeyboardMarkup]:
    message_text= ""
    every_post_message = ""
    added_count = 0
    counter = 1
    for post in posts:
        if post["status"] == "OK":
           every_post_message += f"{counter}. ✅ ID поста: #{post["post_id"]}\n"
           added_count += 1
        elif post["status"] == "DELETED":
            every_post_message += f"{counter}. 🗑 <s>ID: #{post["post_id"]} (Удален)</s>\n"
        else:
            every_post_message += f"{counter}. ❌ Ошибка: {post["status"]}\n"
        counter += 1
    

    message_text = (f"Добавлено {added_count} постов в очередь!\n\n")
    
    message_text += every_post_message

    builder = InlineKeyboardBuilder()
    main_menu_btn = InlineKeyboardButton(text="Показать главную страницу", callback_data=AdminCB.RETURN_MAIN)
    
    
    for post in posts:
        if post["status"] == "OK":
            builder.row(InlineKeyboardButton(text=f"🗑 #{post['post_id']}", callback_data=DeletePostCB(id=post['post_id'], source="mass_posting", page=-1).pack()))

    builder.row(main_menu_btn)

    
    return message_text, builder.as_markup()