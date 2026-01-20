from aiogram.fsm.state import StatesGroup, State

class AdminPanel(StatesGroup):
    main_page = State()
    delete_posts_confirmation = State()
    post_queue_page = State()
    add_post_for_date_page = State()