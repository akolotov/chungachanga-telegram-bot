from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Any, List, Tuple, Type
import os
from enum import Enum

class AgentEngine(str, Enum):
    GEMINI = "gemini"
    OPENAI = "openai"

class ElevenLabsRotateMethod(str, Enum):
    BASIC = "basic"
    ROUND_ROBIN = "round-robin"

class Settings(BaseSettings):
    telegram_bot_token: str = Field(default="", env="TELEGRAM_BOT_TOKEN")
    telegram_channel_id: str = Field(default="", env="TELEGRAM_CHANNEL_ID")
    telegram_discussion_group_id: str = Field(default="", env="TELEGRAM_DISCUSSION_GROUP_ID")
    telegram_operators: str = Field(default="", env="TELEGRAM_OPERATORS")
    disable_voice_notes: bool = Field(default=False, env="DISABLE_VOICE_NOTES")
    agent_engine: AgentEngine = Field(default=AgentEngine.GEMINI, env="AGENT_ENGINE")
    agent_engine_api_key: str = Field(default="", env="AGENT_ENGINE_API_KEY")
    agent_engine_model: str = Field(default="gemini-1.5-flash-002", env="AGENT_ENGINE_MODEL")
    elevenlabs_api_key: str = Field(efault="", env="ELEVENLABS_API_KEY")
    elevenlabs_rotate_method: ElevenLabsRotateMethod = Field(default=ElevenLabsRotateMethod.BASIC, env="ELEVENLABS_ROTATE_METHOD")
    audio_output_dir: str = Field(default=os.path.join("data", "audio"), env="AUDIO_OUTPUT_DIR")
    content_output_dir: str = Field(default=os.path.join("data", "content"), env="CONTENT_OUTPUT_DIR")
    transcript_output_dir: str = Field(default=os.path.join("data", "transcript"), env="TRANSCRIPT_OUTPUT_DIR")
    translation_output_dir: str = Field(default=os.path.join("data", "translation"), env="TRANSLATION_OUTPUT_DIR")
    content_db: str = Field(default=os.path.join("data", "content_db.json"), env="CONTENT_DB")
    url_link: str = Field(default="", env="URL_LINK")

    def get_telegram_operators(self) -> List[str]:
        return [x for x in self.telegram_operators.split(',')]
    
    def get_elevenlabs_api_keys(self) -> List[str]:
        return [x for x in self.elevenlabs_api_key.split(',')]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Create a single settings instance to be used throughout the application
settings = Settings() 