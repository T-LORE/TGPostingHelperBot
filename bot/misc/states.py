from aiogram.fsm.state import StatesGroup, State

class AdminPanel(StatesGroup):
    main_page = State()
    delete_posts_confirmation = State()
    post_queue_page = State()
    add_post_for_date_page = State()
    config_edit_timestamps = State()
    config_wait_time = State()
    config_wait_caption = State()
    config_wait_time_new = State()