import logging
from contextlib import suppress
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.types import LinkPreviewOptions


from bot.misc.states import AdminPanel
from bot.misc.callbacks import AdminCB, ConfigSlotCB
from bot.misc.config import config, ScheduleSlot
import bot.windows.admin as window


router = Router()

logger = logging.getLogger(__name__)

@router.callback_query(
        F.data == AdminCB.EDIT_CONGFIG_MENU
        )
async def config_menu(callback: CallbackQuery, state: FSMContext):
    message_text, reply_markup = await window.get_config_main_window()

    await callback.message.edit_text(message_text, reply_markup=reply_markup)
    await state.set_state(AdminPanel.config_edit_timestamps)
    await callback.answer()

@router.callback_query(
        ConfigSlotCB.filter(F.action == "select")
        )
async def select_slot(callback: CallbackQuery, callback_data: ConfigSlotCB, state: FSMContext):
    index = callback_data.index
    text, kb = window.get_slot_edit_window(index)
    
    await callback.message.edit_text(text, reply_markup=kb)
    await state.update_data(editing_slot_index=index)
    await callback.answer()

@router.callback_query(
        ConfigSlotCB.filter(F.action == "delete")
        )
async def delete_slot(callback: CallbackQuery, callback_data: ConfigSlotCB):
    index = callback_data.index
    
    if 0 <= index < len(config.post_timestamps):
        deleted_time = config.post_timestamps.pop(index)
        config.save()
        await callback.answer(f"Слот {deleted_time.time} удален")
    else:
        await callback.answer("Ошибка: слот не найден", show_alert=True)
    
    text, kb = await window.get_config_main_window() 
    await callback.message.edit_text(text, reply_markup=kb)

@router.callback_query(
        ConfigSlotCB.filter(F.action == "edit_time")
        )
async def start_edit_time(callback: CallbackQuery, callback_data: ConfigSlotCB, state: FSMContext):
    await state.update_data(editing_slot_index=callback_data.index)
    
    await callback.message.edit_text("⏰ <b>Введите новое время</b> в формате <code>HH:MM</code> (например, 14:30):", reply_markup=window.get_cancel_edit_keyboard())
    await state.set_state(AdminPanel.config_wait_time)
    await callback.answer()

@router.message(
        StateFilter(AdminPanel.config_wait_time)
        )
async def process_new_time(message: Message, state: FSMContext):
    new_time_str = message.text.strip()
    
    try:
        dt = datetime.strptime(new_time_str, "%H:%M")
        clean_time = dt.strftime("%H:%M")
    except ValueError:
        await message.reply("❌ Неверный формат! Используйте <code>HH:MM</code> (например, 09:00). Попробуйте еще раз.", reply_markup=window.get_cancel_edit_keyboard())
        return

    data = await state.get_data()
    index = data.get("editing_slot_index")
    
    if index is None or index >= len(config.post_timestamps):
        await message.reply("Ошибка: слот не найден. Начните сначала.")
        await state.set_state(AdminPanel.config_edit_timestamps)
        return

    config.post_timestamps[index].time = clean_time
    config.save()
    
    await message.reply(f"✅ Время изменено на <b>{clean_time}</b>")
    
    text, kb = window.get_slot_edit_window(index)
    await message.answer(text, reply_markup=kb)
    await state.set_state(AdminPanel.config_edit_timestamps)

@router.callback_query(
        ConfigSlotCB.filter(F.action == "edit_caption")
        )
async def start_edit_caption(callback: CallbackQuery, callback_data: ConfigSlotCB, state: FSMContext):
    await state.update_data(editing_slot_index=callback_data.index)
    
    await callback.message.edit_text(
        "📝 <b>Пришлите новую подпись</b>:", 
        reply_markup=window.get_cancel_edit_keyboard()
    )
    await state.set_state(AdminPanel.config_wait_caption)
    await callback.answer()

@router.message(
        StateFilter(AdminPanel.config_wait_caption)
        )
async def process_new_caption(message: Message, state: FSMContext):
    new_caption = message.html_text if message.html_text else message.text
    
    data = await state.get_data()
    index = data.get("editing_slot_index")
    
    if index is not None and 0 <= index < len(config.post_timestamps):
        config.post_timestamps[index].caption = new_caption
        config.save()
        await message.reply("✅ Подпись обновлена!")
        
        text, kb = window.get_slot_edit_window(index)
        await message.answer(text, reply_markup=kb)
    else:
        await message.reply("Ошибка сохранения.")
        
    await state.set_state(AdminPanel.config_edit_timestamps)

@router.callback_query(
        F.data == AdminCB.CANCEL_EDIT_SLOT
        )
async def cancel_edit(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    index = data.get("editing_slot_index")
    
    if index is not None:
        text, kb = window.get_slot_edit_window(index)
        await callback.message.edit_text(text, reply_markup=kb)
    else:
        text, kb = await window.get_config_main_window()
        await callback.message.edit_text(text, reply_markup=kb)
        
    await state.set_state(AdminPanel.config_edit_timestamps)
    await callback.answer()

@router.callback_query(
        F.data == AdminCB.ADD_CONFIG_SLOT
        )
async def start_add_slot(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "➕ <b>Добавление нового слота</b>\n\n"
        "Введите время в формате <code>HH:MM</code> (например, 15:00):",
        reply_markup=window.get_cancel_edit_keyboard()
    )
    await state.set_state(AdminPanel.config_wait_time_new)
    await callback.answer()

@router.message(
        StateFilter(AdminPanel.config_wait_time_new)
        )
async def process_add_slot_time(message: Message, state: FSMContext):
    new_time_str = message.text.strip()
    
    try:
        dt = datetime.strptime(new_time_str, "%H:%M")
        clean_time = dt.strftime("%H:%M")
    except ValueError:
        await message.reply(
            "❌ Неверный формат! Введите время как <code>HH:MM</code> (например, 09:30).",
            reply_markup=window.get_cancel_edit_keyboard()
        )
        return

    for slot in config.post_timestamps:
        if slot.time == clean_time:
            await message.reply(
                f"⚠️ Слот на <b>{clean_time}</b> уже существует!",
                reply_markup=window.get_cancel_edit_keyboard()
            )
            return

    default_caption = "Заглушка"
    
    new_slot = ScheduleSlot(time=clean_time, caption=default_caption)
    
    config.post_timestamps.append(new_slot)
    
    config.post_timestamps.sort(key=lambda x: datetime.strptime(x.time, "%H:%M"))
    
    config.save()
    
    await message.reply(f"✅ Слот <b>{clean_time}</b> успешно добавлен!")
    
    text, kb = await window.get_config_main_window()
    await message.answer(text, reply_markup=kb)
    
    await state.set_state(AdminPanel.config_edit_timestamps)
