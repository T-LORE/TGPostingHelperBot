from aiogram.types import Message

from bot.misc.config import env, config
from bot.misc.util import get_next_posts_datetime
from bot.database.requests import add_to_queue

MAX_FILE_SIZE = 20*1024*1024

async def enqueue_messages_media(messages_list: list[Message]):
    response = {
        "added_count": 0,
        "posts": []
    }

    dates_list = await get_next_posts_datetime(len(messages_list))

    for msg, publish_date in zip(messages_list, dates_list):
        file_id = None
        media_type = 'photo'
        post = {
            "post_id": -1,
            "status": ""
        }
        if msg.photo:
            if msg.photo[-1].file_size > MAX_FILE_SIZE:
                post['status']= "File too big!"
            else:
                file_id = msg.photo[-1].file_id
                await msg.bot.download(
                    msg.photo[-1],
                    destination=f"{env.media_storage_path}/{file_id}.jpg"
                )
                media_type = 'photo'
        elif msg.video:
            if msg.video.file_size > MAX_FILE_SIZE:
                post['status']= "File too big!"
            else:
                file_id = msg.video.file_id
                await msg.bot.download(
                    msg.video,
                    destination=f"{env.media_storage_path}/{file_id}.mp4"
                )
                media_type = 'video'
        elif msg.animation:
            if msg.animation.file_size > MAX_FILE_SIZE:
                post['status']= "File too big!"
            else:
                file_id = msg.animation.file_id
                await msg.bot.download(
                    msg.animation,
                    destination=f"{env.media_storage_path}/{file_id}.gif"
                )
                media_type = 'animation'
          
        if file_id:
            post_id = await add_to_queue(file_id=file_id, caption=config.post_caption, media_type=media_type, publish_date=publish_date)
            post['status'] = 'OK'
            post['post_id'] = post_id
            response['added_count'] += 1

        response["posts"].append(post)


    return response

