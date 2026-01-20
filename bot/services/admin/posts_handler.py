from datetime import datetime
import logging

from aiogram.types import Message

from bot.misc.config import env, config
from bot.misc.util import get_next_post_slot
from bot.database.requests import delete_all_posts, delete_post, get_post, add_to_queue, get_tg_scheduled_posts, get_latest_posts
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

        latest_posts = await get_latest_posts(start_post=0, posts_amount=1)
        
        if latest_posts and len(latest_posts) > 0:
            current_cursor_date = latest_posts[0]['publish_date']
        else:
            current_cursor_date = datetime.now()

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
        return False, "Post not found"

    if post['tg_message_id']:
        is_tg_contain = await is_tg_contain_post(post['tg_message_id'])
        if not is_tg_contain:
            logger.warning(f"Can't find post #{post_id} with message id #{post['tg_message_id']} in TG")
        else:
            is_deleted, error = await delete_posts_from_tg([post['tg_message_id']])
            if not is_deleted:
                logger.warning(f"Deleting post #{post_id} aborted with error: {error}")
                return False, error

    
    await delete_post(post_id)
    logger.info(f"Post #{post_id} deleted from queue")
    return True, "OK"

async def update_tg_schedule():
    posted, not_posted = await upload_posts_to_schedule()
    return posted, not_posted