from datetime import datetime
import textwrap
import re

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.misc.callbacks import AdminCB, ConfigSlotCB
from bot.misc.config import config

MAX_CAPTION_LENGTH = 10

async def get_config_main_window() -> tuple[str, InlineKeyboardMarkup]:
    indexed_slots = []
    for i, slot in enumerate(config.post_timestamps):
        dt = datetime.strptime(slot.time.strip(), "%H:%M")
        indexed_slots.append({"index": i, "dt": dt, "slot": slot})
    
    indexed_slots.sort(key=lambda x: x["dt"])

    groups = {
        "🌅 Утро (06-12)": [],
        "☀️ День (12-18)": [],
        "🌆 Вечер (18-00)": [],
        "🌙 Ночь (00-06)": []
    }

    for item in indexed_slots:
        h = item["dt"].hour
        if 6 <= h < 12:
            groups["🌅 Утро (06-12)"].append(item)
        elif 12 <= h < 18:
            groups["☀️ День (12-18)"].append(item)
        elif 18 <= h <= 23:
            groups["🌆 Вечер (18-00)"].append(item)
        else:
            groups["🌙 Ночь (00-06)"].append(item)

    text_parts = []
    
    for group_name, items in groups.items():
        if not items: continue # Пропускаем пустые группы
        
        group_text = f"<b>{group_name}:</b>"
        
        for item in items:
            slot = item["slot"]
            time_str = f"<code>{slot.time}</code>"
            
            clean = clear_html_tags(slot.caption).replace("\n", " ").strip()
            short = (clean[:MAX_CAPTION_LENGTH] + '..') if len(clean) > MAX_CAPTION_LENGTH else clean
            desc = f"{short}"
        
            group_text += f"\n• {time_str} — {desc}"
        
        text_parts.append(group_text)

    schedule_view = "\n\n".join(text_parts) if text_parts else "<i>Расписание пусто</i>"

    message_text = f"""
<b>⚙️ РЕДАКТОР РАСПИСАНИЯ</b>
🌍 Таймзона: <code>{config.timezone}</code>
➖➖➖➖➖➖➖➖➖➖
{schedule_view}
➖➖➖➖➖➖➖➖➖➖
<i>Нажмите на время для редактирования:</i>
"""

    builder = InlineKeyboardBuilder()
    
    slot_buttons = []
    for item in indexed_slots:
        slot_buttons.append(InlineKeyboardButton(
            text=item["slot"].time,
            callback_data=ConfigSlotCB(action="select", index=item["index"]).pack()
        ))
    
    builder.row(*slot_buttons, width=4)

    builder.row(InlineKeyboardButton(text="➕ Добавить новый слот", callback_data=AdminCB.ADD_CONFIG_SLOT))
    builder.row(InlineKeyboardButton(text="🔙 Назад в меню", callback_data=AdminCB.RETURN_MAIN_EDIT))

    return message_text.strip(), builder.as_markup()

def get_slot_edit_window(slot_index: int) -> tuple[str, InlineKeyboardMarkup]:
    try:
        slot = config.post_timestamps[slot_index]
    except IndexError:
        return "❌ Слот не найден", InlineKeyboardBuilder().as_markup()

    text = f"""
✏️ <b>Настройка слота {slot.time}</b>

📝 <b>Текущая подпись:</b>
➖➖➖➖➖➖➖➖➖➖
{slot.caption}
➖➖➖➖➖➖➖➖➖➖
Выберите действие:
"""
    
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(
        text="⏰ Изменить время",
        callback_data=ConfigSlotCB(action="edit_time", index=slot_index).pack()
    ))
    builder.row(InlineKeyboardButton(
        text="📝 Изменить подпись",
        callback_data=ConfigSlotCB(action="edit_caption", index=slot_index).pack()
    ))
    builder.row(InlineKeyboardButton(
        text="🗑 Удалить слот",
        callback_data=ConfigSlotCB(action="delete", index=slot_index).pack()
    ))
    builder.row(InlineKeyboardButton(
        text="🔙 Назад к списку",
        callback_data=AdminCB.EDIT_CONGFIG_MENU
    ))

    return text, builder.as_markup()

def get_cancel_edit_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data=AdminCB.CANCEL_EDIT_SLOT))
    return builder.as_markup()

def clear_html_tags(text):
    regex = re.compile(r'<.*?>')
    return regex.sub('', text)