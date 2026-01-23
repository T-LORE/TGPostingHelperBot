from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command, CommandObject
from aiogram.types import LinkPreviewOptions

from bot.database.requests import add_admin_to_db, remove_admin_from_db, get_all_admins
from bot.misc.config import env
from bot.services.schedule_poster import resolve_username_to_id, resolve_id_to_info

router = Router()

@router.message(Command("add_admin"))
async def cmd_add_admin(message: Message, command: CommandObject):
    if not command.args:
        await message.reply("⚠️ Ошибка. Формат: <code>/add_admin 12345</code> или <code>/add_admin @username</code>")
        return

    admin_arg = command.args.strip()
    new_admin_id = None

    if admin_arg.isdigit():
        new_admin_id = int(admin_arg)
        
    else:
        await message.answer("🔄 Ищу пользователя в базе Telegram...")
        new_admin_id = await resolve_username_to_id(admin_arg)
        
        if new_admin_id is None:
            await message.reply(f"❌ Не удалось найти пользователя <code>{admin_arg}</code>.\nПроверьте правильность юзернейма.")
            return

    is_added = await add_admin_to_db(new_admin_id, "admin")

    if is_added:
        await message.reply(f"✅ Пользователь <code>{new_admin_id}</code> ({admin_arg}) назначен администратором.")
    else:
        await message.reply(f"ℹ️ Пользователь <code>{new_admin_id}</code> уже является администратором.")


@router.message(Command("del_admin"))
async def cmd_del_admin(message: Message, command: CommandObject):
    if not command.args:
        await message.reply("⚠️ Ошибка. Формат: <code>/del_admin 12345</code> или <code>/del_admin @username</code>")
        return

    admin_arg = command.args.strip()
    target_id = None

    if admin_arg.isdigit():
        target_id = int(admin_arg)
        
    else:
        await message.answer("🔄 Ищу ID по юзернейму...")
        target_id = await resolve_username_to_id(admin_arg)
        
        if target_id is None:
            await message.reply(f"❌ Не удалось найти пользователя <code>{admin_arg}</code>.")
            return

    if target_id == env.root_admin_id:
        await message.reply("⛔️ <b>Нельзя удалить Владельца бота.</b>")
        return
    
    if target_id == message.from_user.id:
        await message.reply("🤨 Нельзя удалить самого себя.")
        return

    is_removed = await remove_admin_from_db(target_id)

    if is_removed:
        await message.reply(f"🗑 Пользователь <code>{target_id}</code> ({admin_arg}) удален.")
    else:
        await message.reply(f"ℹ️ ID <code>{target_id}</code> не найден в списке админов.")


@router.message(Command("admins"))
async def cmd_list_admins(message: Message):
    admins_ids = await get_all_admins()
    
    text = "👮‍♂️ <b>Список администраторов:</b>\n\n"
    
    for admin_id in admins_ids:
        info = await resolve_id_to_info(admin_id)
        
        role = "👑[Владелец]" if admin_id == env.root_admin_id else "[Админ]"
        
        user_link = info['link']
        
        username_text = f"({info['username']})" if info['username'] else ""
        
        text += f"{role} {user_link} {username_text}\n"
        
    await message.reply(
        text=text,
        link_preview_options=LinkPreviewOptions(is_disabled=True)
    )