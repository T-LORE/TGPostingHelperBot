from aiogram import Router
from bot.filters.admin import IsAdmin
from bot.middlewares.album import AlbumMiddleware

from .routers import main_menu, queue_list, delete_all, unknown

admin_router = Router()

admin_router.message.filter(IsAdmin())
admin_router.message.middleware(AlbumMiddleware(latency=0.5))


admin_router.include_routers(
    main_menu.router,   
    queue_list.router,  
    delete_all.router,  
    unknown.router 
)