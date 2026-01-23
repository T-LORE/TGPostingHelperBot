import logging
import asyncio
import datetime
import os

from telethon import TelegramClient
from telethon.tl import types, functions
from telethon.tl.custom.message import Message
from telethon.errors import FloodWaitError

from bot.misc.config import env, config
from bot.database.requests import get_not_tg_scheduled_posts, update_post_tg_id, get_not_published_posts, get_tg_scheduled_posts
from bot.misc.util import convert_timezone

logger = logging.getLogger(__name__)

client = TelegramClient(env.session_name, env.api_id, env.api_hash)

async def start_telethon():
    await client.start()
    logger.info("Telethon Client started successfully.")

async def stop_telethon():
    await client.disconnect()

async def upload_posts_to_schedule():
    logger.info("Poster: Clearing media folder...")
    removed_files = await clear_media_folder()

    logger.info(f"Poster: Removed {len(removed_files)} files")

    logger.info("Poster: Checking for new posts to schedule...")
    response = {
        "status": "UNKNOWN",
        "posts": [],
    }

    # try:
    posts_to_upload, expired_posts = await get_posts_to_upload()
    
    for post in expired_posts:
            response["posts"].append({
            "id": post['id'],
            "tg_message_id": None,
            "status": "EXPIRED"
        })
    
    if len(posts_to_upload) <= 0:
        logger.info(f"Poster: Skip task")
        response["status"] = "SKIP"
        return response

    posts_to_remove = await get_posts_to_remove_from_schedule(posts_to_upload)

    logger.info(f"Poster: posts to upload: {len(posts_to_upload)} posts to remove: {len(posts_to_remove)}")

    remove_res = await delete_posts_from_tg(posts_to_remove)

    response["posts"] += remove_res

    not_uploaded = []
    for post in posts_to_upload:
        if post["tg_message_id"] is None:
            not_uploaded.append(post)

    upload_res = await upload_posts_to_tg(not_uploaded)

    response["posts"] += upload_res["posts"]

    logger.info(f"Poster: Done!")   

    response["status"] = "OK"

    return response

    # except Exception as e:
    #     logger.error(f"Poster: Error: {e}")
    #     response["status"] = f"{str(e)}"
    #     return response



async def get_posts_to_upload():
    not_published_posts = await get_not_published_posts() 
    
    if not_published_posts is None and len(not_published_posts) == 0:
        logger.info(f"Poster: There is no posts in queue")
        return []

    expired_posts = []
    slots = await calculate_under_control_slots()
    
    for post in not_published_posts:
        if post["publish_date"] <= datetime.datetime.now():
            logger.warning(f"Poster: post #{post['id']} skipped his publish date: {post['publish_date']}!")
            expired_posts.append(post)
            not_published_posts.remove(post)

    if len(not_published_posts) <= slots:
        return not_published_posts, expired_posts
    else:
        return not_published_posts[:slots], expired_posts
    
async def get_posts_to_remove_from_schedule(posts_to_upload):
    current_tg_scheduled = await get_tg_scheduled_posts()
    posts_to_remove = []
    
    for tg_post in current_tg_scheduled:
        if tg_post not in posts_to_upload:
            posts_to_remove.append(tg_post)
    
    return posts_to_remove
    
        
async def calculate_under_control_slots():
    current_tg_scheduled_count = await get_scheduled_messages_count()
    my_scheduled_posts = await get_tg_scheduled_posts()
    spots_available = config.max_tg_buffer_size - current_tg_scheduled_count

    slots_under_control = max(config.max_tg_buffer_size - current_tg_scheduled_count + len(my_scheduled_posts), len(my_scheduled_posts))
    slots_under_control = min(config.max_tg_buffer_size, slots_under_control)

    logger.info(f"Poster: Availiable spots: {max(0, spots_available)}/{config.max_tg_buffer_size}, spots under control: {slots_under_control}")

    return slots_under_control
 
async def upload_posts_to_tg(posts: list[dict]) -> list[dict]:
    response = {
        "status": "UNKNOWN",
        "posts": []
    }

    try:
        if not client.is_connected():
            await client.connect()

        channel_peer = await client.get_input_entity(env.channel_id)

        for post in posts:
            try:
                post_response ={
                    "id": post['id'],
                    "tg_message_id": None,
                    "status": "UNKNOWN"
                }

                if post["tg_message_id"] is not None:
                    logger.info(f"Poster: post #{post['id']} already scheduled")
                    post_response["status"] = "SCHEDULED"
                    response["posts"].append(post_response)
                    continue
                
                sent_message = await client.send_message(
                    entity=channel_peer,
                    message=post['caption'],
                    schedule=convert_timezone(post['publish_date']),
                    file=get_file_path(post['file_id']),
                    parse_mode='html'
                )

                tg_msg_id = sent_message.id
                await update_post_tg_id(post['id'], tg_msg_id)

                logger.info(f"Poster: SUCCESS post #{post['id']} for {post['publish_date']} -> TG ID: {tg_msg_id}")

                post_response["tg_message_id"] = tg_msg_id
                post_response["status"] = "SCHEDULED"

                response["posts"].append(post_response)

                await asyncio.sleep(1.5)
                
            except FloodWaitError as e:
                logger.error(f"Poster: Failed to schedule post #{post['id']}, flood wait: {e.seconds}")
                post_response["status"] = f"FLOOD_WAIT_{e.seconds}"
                response["posts"].append(post_response)
                await asyncio.sleep(1.5)

            except Exception as e:
                logger.error(f"Poster: Failed to schedule post #{post['id']}: {e}") 
                post_response["status"] = f"{str(e)}"
                response["posts"].append(post_response)
                await asyncio.sleep(1.5)
    
    except Exception as e:
        logger.error(f"Poster: Global error during upload posts: {e}")
        
        for post in posts:
            response["status"] = f"{str(e)}"
        return response

    response["status"] = "OK"
    return response

def get_file_path(file_id: str):
    for root, dirs, files in os.walk(env.media_storage_path):
        for file in files:
            if file.startswith(file_id):
                return os.path.join(root, file)
    return None

async def delete_posts_from_tg(posts: list) -> list[dict]:
    tg_map = {}
    tg_ids_to_delete = []
    final_report = []

    for post in posts:
        tg_id = post['tg_message_id']
        db_id = post['id']

        if tg_id:
            tg_map[tg_id] = db_id
            tg_ids_to_delete.append(tg_id)
        else:
            final_report.append({
                "id": db_id,
                "tg_message_id": None,
                "status": "DELETED", 
            })

    if len(tg_ids_to_delete) == 0:
        if len(final_report) > 0:
            logger.warning("Poster: provided posts are already deleted from telegram")
        else:
            logger.warning("Poster: provided posts are empty")
        return final_report
    
    result = await delete_messages_from_tg(tg_ids_to_delete)

    for msg_res in result:
        tg_id = msg_res['tg_message_id']
        status = msg_res['status']
        
        db_post_id = tg_map.get(tg_id)

        if status == 'DELETED':
            await update_post_tg_id(db_post_id, None)
        else:
            logger.warning(f"Poster: Failed to delete scheduled post #{db_post_id} with message id #{tg_id} from TG")

        final_report.append({
            "id": db_post_id,
            "tg_message_id": tg_id,
            "status": status
        })

    return final_report

async def delete_messages_from_tg(tg_message_ids: list[int]) -> list[dict]:

    result = []

    if not tg_message_ids:
        logger.warning("Poster: No messages provided to delete")
        return result

    try:
        if not client.is_connected():
            await client.connect()

        channel_peer = await client.get_input_entity(env.channel_id)

        api_result = await client(functions.messages.DeleteScheduledMessagesRequest(
            peer=channel_peer,
            id=tg_message_ids
        ))
        logger.debug(f"Poster: Delete result: {api_result}")
        actually_deleted_ids = set()
        
        if hasattr(api_result, 'updates'):
            for update in api_result.updates:
                if isinstance(update, types.UpdateDeleteScheduledMessages):
                    actually_deleted_ids.update(update.messages)
        
        for msg_id in tg_message_ids:
            msg_report = {
                "tg_message_id": msg_id,
                "status": "UNKNOWN",
            }
            
            if msg_id in actually_deleted_ids:
                msg_report["status"] = "DELETED"
            else:
                msg_report["status"] = "NOT_DELETED"
                logger.warning(f"Poster: Message {msg_id} not deleted")
            
            result.append(msg_report)

        logger.info(f"Poster: Batch delete result: {len(actually_deleted_ids)}/{len(tg_message_ids)} deleted.")
        return result

    except Exception as e:
        logger.error(f"Poster: Global error during batch delete: {e}")
        
        for msg_id in tg_message_ids:
           result.append({
                "tg_message_id": msg_id,
                "status": str(e),
            })
            
        return result

async def is_tg_contain_post(message_id: int):
    try:
        channel_peer = await client.get_input_entity(env.channel_id)
        scheduled_messages = await client(functions.messages.GetScheduledHistoryRequest(
            peer=channel_peer,
            hash=0
        ))

    except Exception as e:
        logger.error(f"Poster: Error checking scheduled messages: {e}")
        return False

    for message in scheduled_messages.messages:
        if message.id == message_id:
            logger.info(f"Poster: Found message {message_id} in TG")
            return True
        
    logger.info(f"Poster: Not found message {message_id} in TG")

    return False

async def clear_media_folder():
    all_files = os.listdir(env.media_storage_path)
    logger.info(f"Poster: Found {len(all_files)} files in media folder")
    necessary_files = []
    removed_files = []

    not_published_posts = await get_not_published_posts()
    
    if not_published_posts is None and len(not_published_posts) == 0:
        return removed_files
    
    necessary_files = [post['file_id'] for post in not_published_posts]
    necessary_files.append("DEFAULT MEDIA STORAGE")
    
    for file in all_files:
        file_name = file.split(".")[0]
        if file_name not in necessary_files:
            logger.info(f"Poster: Remove file {file}")
            removed_files.append(file)
            os.remove(os.path.join(env.media_storage_path, file))

    return removed_files

# TODO: cache
async def get_scheduled_messages_count():
    try:
        channel_peer = await client.get_input_entity(env.channel_id)
        scheduled_messages = await client(functions.messages.GetScheduledHistoryRequest(
            peer=channel_peer,
            hash=0
        ))
        logger.info(f"Poster: current tg schedule count: {scheduled_messages.count}")
        return scheduled_messages.count
    except Exception as e:
        logger.error(f"Poster: Error checking scheduled messages: {e}")
        return -1