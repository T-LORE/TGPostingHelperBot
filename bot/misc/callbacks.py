from aiogram.filters.callback_data import CallbackData

class AdminCB:
    UPDATE = "update_main_page"
    DELETE_ALL_CONFIRM = "delete_all_posts_confirmation"
    DELETE_ALL = "delete_all_posts"
    POST_QUEUE = "posts_enqueued"
    UPDATE_TG_SCHEDULE = "update_tg_schedule"
    
    CLOSE_POST = "close_post"

    RETURN_MAIN = "return_to_main_page"
    RETURN_MAIN_EDIT = "return_to_main_page_with_edit"
    RETURN_MAIN_DELETE = "return_to_main_page_with_delete"


class NavigationCB(CallbackData, prefix="nav"):
    page: int

class DeletePostCB(CallbackData, prefix="delpost"):
    id: int     
    page: int
    source: str

class ViewPostCB(CallbackData, prefix="viewpost"):
    id: int
    page: int

class DateViewCB(CallbackData, prefix="dateview"):
    day: int
    month: int
    year: int

class AddPostCB(CallbackData, prefix="addpost"):
    day: int
    month: int
    year: int
    hour: int
    minute: int