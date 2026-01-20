import asyncio
from typing import Any, Dict, Union, List, Callable, Awaitable
import logging

from aiogram import BaseMiddleware
from aiogram.types import Message

logger = logging.getLogger(__name__)

class AlbumMiddleware(BaseMiddleware):
    def __init__(self, latency: Union[int, float] = 0.5):
        self.latency = latency
        self.album_data = {}

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:       
        if not event.media_group_id:
            return await handler(event, data)

        group_id = event.media_group_id
        
        if group_id not in self.album_data:
            
            self.album_data[group_id] = []
            self.album_data[group_id].append(event)
            
            await asyncio.sleep(self.latency)

            my_album: List[Message] = self.album_data[group_id]
            my_album.sort(key=lambda x: x.message_id)

            data["album"] = my_album
            
            del self.album_data[group_id]
            logger.info(f"Album with {len(data["album"])} elements detected in group_id {group_id}")
            return await handler(event, data)

        else:
            self.album_data[group_id].append(event)
            return