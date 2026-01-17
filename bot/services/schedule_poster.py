import logging
import time
import datetime
import os

from telethon import TelegramClient
from telethon.tl import types, functions
from telethon.tl.custom.message import Message

from bot.misc.config import env, config
from bot.database.requests import get_not_uploaded_posts, update_post_tg_id

logger = logging.getLogger(__name__)

client = TelegramClient(env.session_name, env.api_id, env.api_hash)

async def start_telethon():
    await client.start()
    logger.info("Telethon Client started successfully.")

async def stop_telethon():
    await client.disconnect()

async def upload_posts_to_schedule():
    logger.info("Poster: Checking for new posts to schedule...")

    try:
        channel_peer = await client.get_input_entity(env.channel_id)
        scheduled_messages = await client(functions.messages.GetScheduledHistoryRequest(
            peer=channel_peer, # PeerChanndel(id)
            hash=0
        ))
        logger.info(f"Poster: current scheduled posts: {scheduled_messages.count}")
    except Exception as e:
        logger.error(f"Poster: Error checking scheduled messages: {e}")
        return   

    spots_available = config.max_tg_buffer_size - scheduled_messages.count
    logger.info(f"Poster: Availiable spots: {max(0, spots_available)}/{config.max_tg_buffer_size}")
    if spots_available <= 0:
        logger.info(f"Poster: Skip task")
        return

    posts = await get_not_uploaded_posts(limit=spots_available)
    
    if not posts:
        logger.info(f"Poster: There is no posts in queue")
        return
    
    logger.info(f"Poster: get {len(posts)} from queue")

    for post in posts:
        try:
            logger.info(f"Poster: process post #{post['id']} for {post['publish_date']}")
            if post['publish_date'] < datetime.datetime.now():
                logger.warning(f"Poster: post #{post['id']} skipped his publish date: {post['publish_date']}!")
                pass
            
            await client.send_message(
                entity=channel_peer,
                message=post['caption'],
                schedule=post['publish_date'],
                file=get_file_path(post['file_id']),
                parse_mode='md'
            )

            logger.info(f"Poster: Scheduled post #{post['id']} for {post['publish_date']}")
            
            #TODO: get message id
            await update_post_tg_id(post['id'], 1)
            
        except Exception as e:
            logger.error(f"Poster: Failed to schedule post #{post['id']}: {e}")
        
        time.sleep(1)

    logger.info(f"Poster: Done!")

def get_file_path(file_id: str):
    for root, dirs, files in os.walk(env.media_storage_path):
        for file in files:
            if file.startswith(file_id):
                return os.path.join(root, file)
    return None
