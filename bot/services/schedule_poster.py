import logging
import asyncio
import datetime
import os

from telethon import TelegramClient
from telethon.tl import types, functions
from telethon.tl.custom.message import Message

from bot.misc.config import env, config
from bot.database.requests import get_not_tg_scheduled_posts, update_post_tg_id, get_not_published_posts
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
    scheduled_posts = []
    exception_posts = []

    try:
        channel_peer = await client.get_input_entity(env.channel_id)
        scheduled_messages = await client(functions.messages.GetScheduledHistoryRequest(
            peer=channel_peer, # PeerChanndel(id)
            hash=0
        ))
        # logger.info("\n" + scheduled_messages.stringify())
        logger.info(f"Poster: current scheduled posts: {scheduled_messages.count}")
    except Exception as e:
        logger.error(f"Poster: Error checking scheduled messages: {e}")
        return scheduled_posts, exception_posts  

    spots_available = config.max_tg_buffer_size - scheduled_messages.count
    logger.info(f"Poster: Availiable spots: {max(0, spots_available)}/{config.max_tg_buffer_size}")
    if spots_available <= 0:
        logger.info(f"Poster: Skip task")
        return scheduled_posts, exception_posts

    posts = await get_not_tg_scheduled_posts(limit=spots_available)
    
    if not posts:
        logger.info(f"Poster: There is no posts in queue")
        return scheduled_posts, exception_posts
    
    logger.info(f"Poster: get {len(posts)} from queue")

    for post in posts:
        try:
            logger.info(f"Poster: process post #{post['id']} for {post['publish_date']}")
            if post['publish_date'] < datetime.datetime.now():
                logger.warning(f"Poster: post #{post['id']} skipped his publish date: {post['publish_date']}!")
                continue
            
            sent_message = await client.send_message(
                entity=channel_peer,
                message=post['caption'],
                schedule=convert_timezone(post['publish_date']),
                file=get_file_path(post['file_id']),
                parse_mode='html'
            )
            tg_msg_id = sent_message.id

            logger.info(f"Poster: SUCCESS post #{post['id']} for {post['publish_date']} -> TG ID: {tg_msg_id}")
            
            await update_post_tg_id(post['id'], tg_msg_id)

            scheduled_posts.append(post)
            
        except Exception as e:
            logger.error(f"Poster: Failed to schedule post #{post['id']}: {e}")
            
            exception_posts.append(post)
        
        await asyncio.sleep(1) 

    logger.info(f"Poster: Done!")

    return scheduled_posts, exception_posts

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
                "post_id": db_id,
                "tg_id": None,
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
            "post_id": db_post_id,
            "tg_id": tg_id,
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