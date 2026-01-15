from contextlib import suppress

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.exceptions import TelegramBadRequest

from bot.filters.admin import IsAdmin
from bot.middlewares.album import AlbumMiddleware
import bot.windows.admin as window
import bot.services.admin as service
from bot.misc.callbacks import AdminCB, NavigationCB, DeletePostCB, ViewPostCB

router = Router()
router.message.filter(IsAdmin())
router.message.middleware(AlbumMiddleware(latency=0.5))

class AdminPanel(StatesGroup):
    main_page = State()
    delete_posts_confirmation = State()
    post_queue_page = State()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    message_text, reply_markup = await window.get_main_menu_window()
    
    await message.answer(message_text,
    reply_markup=reply_markup)

    await state.set_state(AdminPanel.main_page)

@router.callback_query(F.data == AdminCB.UPDATE)
async def update_main_page(callback: CallbackQuery):
    message_text, reply_markup = await window.get_main_menu_window()
        
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(message_text, reply_markup=reply_markup)
    
    await callback.answer()

@router.callback_query(F.data == AdminCB.DELETE_ALL_CONFIRM)
async def delete_all_posts_confirmation(callback: CallbackQuery, state: FSMContext):
    message_text, reply_markup = await window.get_delete_all_posts_confirmation()
    
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(message_text, reply_markup=reply_markup)
    
    await state.set_state(AdminPanel.delete_posts_confirmation)

    await callback.answer()

@router.callback_query(
        AdminPanel.delete_posts_confirmation,
        F.data == AdminCB.DELETE_ALL
        )
async def delete_all_posts(callback: CallbackQuery, state: FSMContext):
    await service.delete_all_posts_from_queue()
    message_text, reply_markup = await window.get_main_menu_window()
    
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(message_text, reply_markup=reply_markup)

    await state.set_state(AdminPanel.main_page)
    
    await callback.answer("Все посты были удалены!", show_alert=True)

@router.callback_query(
        AdminPanel.main_page,
        F.data == AdminCB.POST_QUEUE
        )
async def post_queue(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminPanel.post_queue_page)
    message_text, reply_markup = await window.get_post_queue_window(1)

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(message_text, reply_markup=reply_markup)

    await state.update_data(list_msg_id=callback.message.message_id)

    await callback.answer()

@router.callback_query(AdminPanel.post_queue_page, NavigationCB.filter())
async def post_queue_navigation(callback: CallbackQuery, callback_data: NavigationCB):
    current_page = callback_data.page
    
    message_text, reply_markup = await window.get_post_queue_window(current_page)

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(message_text, reply_markup=reply_markup)
    
    await callback.answer()

@router.callback_query(AdminPanel.post_queue_page, DeletePostCB.filter())
async def delete_post_btn_clicked(callback: CallbackQuery, callback_data: DeletePostCB, state: FSMContext):
    post_id = callback_data.id
    current_page = callback_data.page

    await service.delete_post(post_id)

    await callback.answer("Пост удален")

    state_data = await state.get_data()
    view_msg_id = state_data.get("opened_post_msg_id")
    opened_post_id = state_data.get("opened_post_id")
    list_msg_id = state_data.get("list_msg_id")
    
    if view_msg_id:
        is_deleting_opened_post_from_list = opened_post_id == post_id
        is_deleting_from_opened_post_btn = callback.message.message_id == view_msg_id
        if is_deleting_opened_post_from_list or is_deleting_from_opened_post_btn:
            with suppress(TelegramBadRequest):
                await callback.message.bot.delete_message(
                    chat_id=callback.message.chat.id,
                    message_id=view_msg_id
                )
    
    message_text, reply_markup = await window.get_post_queue_window(current_page)

    with suppress(TelegramBadRequest):
        await callback.message.bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=list_msg_id,
            text=message_text,
            reply_markup=reply_markup)    

@router.callback_query(
        AdminPanel.post_queue_page, 
        ViewPostCB.filter()
        )
async def view_post_btn_clicked(callback: CallbackQuery, callback_data: ViewPostCB, state: FSMContext):
    post_id = callback_data.id
    current_page = callback_data.page
    
    data = await window.get_post_view_window(post_id, current_page)

    if data is None:
        await callback.answer("Пост не найден")
        return
    
    state_data = await state.get_data()
    old_view_msg_id = state_data.get("opened_post_msg_id")

    if old_view_msg_id:
        with suppress(TelegramBadRequest):
            await callback.message.bot.delete_message(
                chat_id=callback.message.chat.id,
                message_id=old_view_msg_id
            )
    
    sent_msg = None

    if data["media_type"] == "photo":
        sent_msg = await callback.message.answer_photo(photo=data["file_id"], caption=data["caption"], reply_markup=data["markup"])
    elif data["media_type"] == "animation":
        sent_msg = await callback.message.answer_animation(animation=data["file_id"], caption=data["caption"], reply_markup=data["markup"])
    elif data["media_type"] == "video":
        sent_msg = await callback.message.answer_video(video=data["file_id"], caption=data["caption"], reply_markup=data["markup"])

    if sent_msg:
        await state.update_data(opened_post_msg_id=sent_msg.message_id, opened_post_id=post_id)

    await callback.answer()

@router.callback_query(
        AdminPanel.post_queue_page, 
        F.data == AdminCB.CLOSE_POST
        )
async def view_post_close_btn_clicked(callback: CallbackQuery, state: FSMContext):      
    await callback.message.delete()

    await state.update_data(opened_post_msg_id=None)

    await callback.answer() 

@router.message(
        AdminPanel.main_page,
        F.photo | F.video | F.animation
        )
async def handle_media_content(message: Message, album: list[Message] = None):
    files_to_process = album if album else [message]
    response = await service.enqueue_messages_media(files_to_process)

    message_text, reply_markup  = await window.get_message_enqueue_answer(response["posts_id"])

    await message.reply(message_text, reply_markup=reply_markup)

@router.message()
async def unknown_command(message: Message):
    message_text, reply_markup = await window.get_unknown_command_window()
    await message.reply(message_text,
    reply_markup=reply_markup)

@router.callback_query(F.data == AdminCB.RETURN_MAIN)
@router.callback_query(F.data == AdminCB.RETURN_MAIN_EDIT)
@router.callback_query(F.data == AdminCB.RETURN_MAIN_DELETE)
async def return_to_main_page(callback: CallbackQuery, state: FSMContext):
    message_text, reply_markup = await window.get_main_menu_window()

    if callback.data == AdminCB.RETURN_MAIN_EDIT:
        with suppress(TelegramBadRequest):
            await callback.message.edit_text(message_text, reply_markup=reply_markup)
    elif callback.data == AdminCB.RETURN_MAIN_DELETE:
        await callback.message.delete()
        await callback.message.answer(message_text, reply_markup=reply_markup)
    elif callback.data == AdminCB.RETURN_MAIN:
        await callback.message.answer(message_text, reply_markup=reply_markup)
        
    await state.set_state(AdminPanel.main_page)

    await callback.answer()