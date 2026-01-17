import os
import logging

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
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

class MutableConfig(BaseModel):
    post_caption: str
    post_timestamps: str
    max_tg_buffer_size: int

    def save(self):
        with open('config.json', 'w', encoding='utf-8') as f:
            f.write(self.model_dump_json(indent=4))

def load_mutable_config() -> MutableConfig:
    logger = logging.getLogger(__name__)

    if not os.path.exists('config.json'):
        logger.warning("Creating new config file")
        default_config = MutableConfig(
            post_caption="Подпись по умолчанию",
            post_timestamps="12:00,13:00,14:00",
            max_tg_buffer_size=80
        )
        default_config.save()
        return default_config
    
    with open('config.json', 'r', encoding='utf-8') as f:
        return MutableConfig.model_validate_json(f.read())

env = EnvSettings()
config = load_mutable_config()