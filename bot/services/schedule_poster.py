import logging
import asyncio
import datetime
import os

from telethon import TelegramClient
from telethon.tl import types, functions
from telethon.tl.custom.message import Message

from bot.misc.config import env, config
from bot.database.requests import get_not_uploaded_posts, update_post_tg_id
from bot.misc.util import convert_timezone

logger = logging.getLogger(__name__)

client = TelegramClient(env.session_name, env.api_id, env.api_hash)

async def start_telethon():
    await client.start()
    logger.info("Telethon Client started successfully.")

async def stop_telethon():
    await client.disconnect()

async def upload_posts_to_schedule():
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

    posts = await get_not_uploaded_posts(limit=spots_available)
    
    if not posts:
        logger.info(f"Poster: There is no posts in queue")
        return scheduled_posts, exception_posts
    
    logger.info(f"Poster: get {len(posts)} from queue")

    for post in posts:
        try:
            logger.info(f"Poster: process post #{post['id']} for {post['publish_date']}")
            if post['publish_date'] < datetime.datetime.now():
                logger.warning(f"Poster: post #{post['id']} skipped his publish date: {post['publish_date']}!")
                pass
            
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

async def delete_posts_from_tg(tg_message_ids: list[int]):
    if not tg_message_ids:
        return

    try:
        if not client.is_connected():
            await client.connect()

        channel_peer = await client.get_input_entity(env.channel_id)

        await client(functions.messages.DeleteScheduledMessagesRequest(
            peer=channel_peer,
            id=tg_message_ids
        ))
        
        logger.info(f"Poster: TG deleted messages ids: {tg_message_ids} ")
        
        return True
        
    except Exception as e:
        logger.error(f"Poster: Failed to delete messages from TG {tg_message_ids}: {e}")

    return False