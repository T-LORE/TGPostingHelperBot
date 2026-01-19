from datetime import datetime
import logging

from aiogram.types import Message

from bot.misc.config import env, config
from bot.misc.util import get_next_post_slot
from bot.database.requests import delete_all_posts, delete_post, get_post, add_to_queue, get_tg_scheduled_posts, get_latest_posts
from bot.services.schedule_poster import delete_posts_from_tg, upload_posts_to_schedule, is_tg_contain_post

MAX_FILE_SIZE = 20*1024*1024

logger = logging.getLogger(__name__)

async def enqueue_messages_media(messages_list: list[Message]):
    response = {
        "added_count": 0,
        "posts": []
    }

    lastest_post = await get_latest_posts(start_post=0, posts_amount=1)
    lastest_post_datetime = datetime.now()

    if lastest_post is not None and len(lastest_post) > 0:
        lastest_post_datetime = lastest_post[0]['publish_date']

    for msg in messages_list:
        file_id = None
        media_type = 'photo'
        post = {
            "post_id": -1,
            "status": ""
        }
        publish_date, caption = await get_next_post_slot(lastest_post_datetime)

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
            post_id = await add_to_queue(file_id=file_id, caption=caption, media_type=media_type, publish_date=publish_date)
            post['status'] = 'OK'
            post['post_id'] = post_id
            response['added_count'] += 1

        response["posts"].append(post)


    return response

async def delete_all_posts_from_queue():
    logger.info("Deleting all posts from queue...")

    posts = await get_tg_scheduled_posts()
    if posts is None or len(posts) == 0:
        logger.info("No posts to delete from TG")
    else:
        ids = [post['tg_message_id'] for post in posts]
        await delete_posts_from_tg(ids)

    await delete_all_posts()
    logger.info("All posts deleted from queue")
    return True

async def delete_post_from_queue(post_id: int):
    logger.info(f"Deleting post #{post_id} from queue...")
    post = await get_post(post_id)

    if post is None:
        logger.warning(f"Can't find post with id {post_id}")
        return False

    if post['tg_message_id']:
        is_tg_contain = await is_tg_contain_post(post['tg_message_id'])
        if not is_tg_contain:
            logger.warning(f"Can't find post #{post_id} with message id #{post['tg_message_id']} in TG")
        else:
            await delete_posts_from_tg([post['tg_message_id']])

    
    await delete_post(post_id)
    logger.info(f"Post #{post_id} deleted from queue")
    return True

async def update_tg_schedule():
    posted, not_posted = await upload_posts_to_schedule()
    return posted, not_posted