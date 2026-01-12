from aiogram.types import Message

from bot.misc.env_config_reader import settings
from bot.misc.util import get_next_posts_datetime
from bot.database.requests import add_to_queue

async def enqueue_messages_media(messages_list: list[Message]):
    response = {
        "added_count": 0,
        "posts_id": []
    }

    dates_list = await get_next_posts_datetime(len(messages_list))

    for msg, publish_date in zip(messages_list, dates_list):
        file_id = None
        media_type = 'photo'
        
        if msg.photo:
            file_id = msg.photo[-1].file_id
            media_type = 'photo'
        elif msg.video:
            file_id = msg.video.file_id
            media_type = 'video'
        elif msg.animation:
            file_id = msg.animation.file_id
            media_type = 'animation'
            
        if file_id:
            post_id = await add_to_queue(file_id=file_id, caption=settings.post_caption, media_type=media_type, publish_date=publish_date)
            response["posts_id"].append(post_id)
            response['added_count'] += 1

    return response