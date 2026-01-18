import os
import logging
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel, SecretStr

class EnvSettings(BaseSettings):
    bot_token: SecretStr
    database_path: str
    root_admin_id: int
    channel_id: int
    api_id: int
    api_hash: str
    session_name: str
    media_storage_path: str
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')


class ScheduleSlot(BaseModel):
    time: str
    caption: str


class MutableConfig(BaseModel):
    max_tg_buffer_size: int
    timezone: str
    post_timestamps: List[ScheduleSlot]

    def save(self):
        with open('config.json', 'w', encoding='utf-8') as f:
            f.write(self.model_dump_json(indent=4))

def load_mutable_config() -> MutableConfig:
    logger = logging.getLogger(__name__)

    if not os.path.exists('config.json'):
        logger.warning("Creating new config file")
        default = MutableConfig(
            max_tg_buffer_size=10,
            timezone="UTC+3",
            post_timestamps=[
                ScheduleSlot(time="10:00", caption="Привет!"),
                ScheduleSlot(time="18:00", caption="Пока!")
            ]
        )
        default.save()
        return default
    
    with open('config.json', 'r', encoding='utf-8') as f:
        return MutableConfig.model_validate_json(f.read())

env = EnvSettings()
config = load_mutable_config()