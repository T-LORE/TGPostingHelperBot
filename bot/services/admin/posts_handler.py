from datetime import datetime
import logging

from aiogram.types import Message

from bot.misc.config import env, config
from bot.misc.util import get_next_post_slot
from bot.database.requests import delete_all_posts, delete_post, get_post, add_to_queue, get_tg_scheduled_posts, get_not_published_posts
from bot.services.schedule_poster import delete_posts_from_tg, upload_posts_to_schedule, is_tg_contain_post
from bot.misc.util import processing_lock

MAX_FILE_SIZE = 20*1024*1024

logger = logging.getLogger(__name__)

async def _process_and_download_media(message: Message) -> tuple[str | None, str | None, str]:
    file_obj = None
    media_type = None
    extension = ""

    if message.photo:
        file_obj = message.photo[-1]
        media_type = 'photo'
        extension = "jpg"
    elif message.video:
        file_obj = message.video
        media_type = 'video'
        extension = "mp4"
    elif message.animation:
        file_obj = message.animation
        media_type = 'animation'
        extension = "gif"
    else:
        return None, None, "Unsupported media type"

    if file_obj.file_size > MAX_FILE_SIZE:
        return None, None, "File too big!"

    try:
        await message.bot.download(
            file_obj,
            destination=f"{env.media_storage_path}/{file_obj.file_id}.{extension}"
        )
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return None, None, "Download failed"

    return file_obj.file_id, media_type, "OK"


async def enqueue_messages_media_for_date(message: Message, publish_date: datetime, caption: str) -> dict:
    file_id, media_type, status = await _process_and_download_media(message)

    post_data = {
        "post_id": -1,
        "status": status
    }

    if file_id:
        post_id = await add_to_queue(
            file_id=file_id, 
            caption=caption, 
            media_type=media_type, 
            publish_date=publish_date
        )
        post_data['post_id'] = post_id
    
    if status != "OK":
        logger.info(f"Post do not added to queue with status {status}")
    else:
        logger.info(f"Post {post_data['post_id']} added to queue at date {publish_date} with status {post_data['status']}")

    return post_data


async def enqueue_messages_media_by_timestamps(messages_list: list[Message]) -> dict:
    async with processing_lock:
        response = {
            "added_count": 0,
            "posts": []
        }

        not_published_posts = await get_not_published_posts()
        current_cursor_date = datetime.now()

        if not_published_posts and len(not_published_posts) > 0:
            if not_published_posts[-1]["publish_date"] > datetime.now():
                current_cursor_date = not_published_posts[-1]["publish_date"]   

        for msg in messages_list:
            publish_date, caption = await get_next_post_slot(current_cursor_date)
            
            current_cursor_date = publish_date

            post_result = await enqueue_messages_media_for_date(msg, publish_date, caption)
            
            if post_result['status'] == 'OK':
                response['added_count'] += 1
                
            response["posts"].append(post_result)

        return response

async def delete_all_posts_from_queue():
    logger.info("Deleting all posts from queue...")
    
    async with processing_lock: 
        posts = await get_tg_scheduled_posts()

        if posts is None or len(posts) == 0:
            logger.info("Nothing to delete")
            return []

    res = await delete_posts(posts)
    
    return res

async def delete_post_from_queue(post_id: int):
    logger.info(f"Deleting post #{post_id} from queue...")
    
    async with processing_lock: 
        post = await get_post(post_id)

        if post is None:
            logger.warning(f"Can't find post with id {post_id}")
            return False, "Post not found"

    res = await delete_posts([post])

    return res[0]

async def delete_posts(posts):
 
    logger.info(f"Deleting {len(posts)} posts from queue...")

    response = []
    posts_response = await delete_posts_from_tg(posts)

    async with processing_lock: 
        for post_response in posts_response:
            response.append(post_response)
            if post_response["status"] == 'DELETED':
                await delete_post(post_response["post_id"])
                logger.info(f"Post #{post_response['post_id']} deleted from queue")
            else:
                logger.warning(f"Deleting post #{post_response['post_id']} aborted with status: {post_response['status']}")
        
    logger.debug(f"Deleting result: {response} ")

    return response


async def update_tg_schedule():
    async with processing_lock:
        posted, not_posted = await upload_posts_to_schedule()
        return posted, not_posted