from aiogram.filters.callback_data import CallbackData

class AdminCB:
    UPDATE = "update_main_page"
    DELETE_ALL_CONFIRM = "delete_all_posts_confirmation"
    DELETE_ALL = "delete_all_posts"
    POST_QUEUE = "posts_enqueued"
    
    RETURN_MAIN = "return_to_main_page"
    RETURN_MAIN_EDIT = "return_to_main_page_with_edit"
    RETURN_MAIN_DELETE = "return_to_main_page_with_delete"


class NavigationCB(CallbackData, prefix="nav"):
    page: int