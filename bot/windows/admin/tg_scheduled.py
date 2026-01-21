from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot.misc.callbacks import AdminCB, DeletePostCB

async def get_tg_scheduled_task_answer(status: str, posts) -> tuple[str, InlineKeyboardMarkup]:
    message_text= ""
    every_post_message = ""
    scheduled_count = 0
    exception_count = 0
    skipped_count = 0
    removed_count = 0
    
    counter = 1
    for post in posts:
        if post["status"] == "SCHEDULED":
            every_post_message += f"{counter}. ✅ ID поста: #{post["id"]}\n"
            scheduled_count += 1
        elif post["status"] == "DELETED":
            every_post_message += f"{counter}. 🗑 ID: #{post["id"]} (Удален из отложки)\n"
            removed_count += 1
        elif post["status"] == "EXPIRED":
            every_post_message += f"{counter}.⚠️ ID: #{post['id']} (Пропущен, просрочен!)\n"
            skipped_count += 1
        elif post["status"].startswith("FLOOD_WAIT_"):
            seconds = post["status"].replace("FLOOD_WAIT_", "")
            every_post_message += f"{counter}.❌ ID: #{post['id']} TG обнаружил флуд, подождите {seconds} секунд\n"
            exception_count += 1
        else:
            every_post_message += f"{counter}. ❌ Ошибка: {post["status"]}\n"
        counter += 1
    
    if status == "SKIP_NO_SPOTS":
        message_text = (f"Задача пропущена, потому что нет свободных слотов!\n\n")
    elif status == "SKIP_NO_POSTS":
        message_text = (f"Задача пропущена, потому что нет постов в очереди!\n\n")
    elif status == "OK":
        message_text = (f"Добавлено {scheduled_count} постов в очередь. Пропущено {skipped_count} постов. Удалено {removed_count} постов. Постов с ошибками: {exception_count}\n\n")
        message_text += every_post_message

    builder = InlineKeyboardBuilder()
    main_menu_btn = InlineKeyboardButton(text="Вернуться на главную", callback_data=AdminCB.RETURN_MAIN_EDIT)

    builder.row(main_menu_btn)

    
    return message_text, builder.as_markup()