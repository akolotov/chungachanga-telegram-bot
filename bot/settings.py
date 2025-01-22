# Python standard library imports
import os
from enum import Enum
from typing import List

# Third-party imports
from pydantic import Field
from pydantic_settings import BaseSettings

# Local imports
from bot.types import LLMEngine

class ElevenLabsRotateMethod(str, Enum):
    BASIC = "basic"
    ROUND_ROBIN = "round-robin"

class Settings(BaseSettings):
    telegram_bot_token: str = Field(default="", env="TELEGRAM_BOT_TOKEN")
    telegram_channel_id: str = Field(default="", env="TELEGRAM_CHANNEL_ID")
    telegram_discussion_group_id: str = Field(default="", env="TELEGRAM_DISCUSSION_GROUP_ID")
    telegram_operators: str = Field(default="", env="TELEGRAM_OPERATORS")
    disable_voice_notes: bool = Field(default=False, env="DISABLE_VOICE_NOTES")
    agent_engine: LLMEngine = Field(default=LLMEngine.GEMINI, env="AGENT_ENGINE")
    agent_engine_api_key: str = Field(default="", env="AGENT_ENGINE_API_KEY")
    agent_engine_model: str = Field(default="gemini-1.5-flash-002", env="AGENT_ENGINE_MODEL")
    keep_raw_engine_responses: bool = Field(default=False, env="KEEP_RAW_ENGINE_RESPONSES")
    raw_engine_responses_dir: str = Field(default=os.path.join("data", "responses"), env="RAW_ENGINE_RESPONSES_DIR")
    elevenlabs_api_key: str = Field(default="", env="ELEVENLABS_API_KEY")
    elevenlabs_rotate_method: ElevenLabsRotateMethod = Field(default=ElevenLabsRotateMethod.BASIC, env="ELEVENLABS_ROTATE_METHOD")
    speech_to_text_api_key: str = Field(default="", env="SPEECH_TO_TEXT_API_KEY")
    audio_output_dir: str = Field(default=os.path.join("data", "audio"), env="AUDIO_OUTPUT_DIR")
    content_output_dir: str = Field(default=os.path.join("data", "content"), env="CONTENT_OUTPUT_DIR")
    transcript_output_dir: str = Field(default=os.path.join("data", "transcript"), env="TRANSCRIPT_OUTPUT_DIR")
    translation_output_dir: str = Field(default=os.path.join("data", "translation"), env="TRANSLATION_OUTPUT_DIR")
    content_db: str = Field(default=os.path.join("data", "content_db.json"), env="CONTENT_DB")
    yt_crhoy_cache_dir: str = Field(default=os.path.join("data", "crhoy", "youtube"), env="YT_CRHOY_CACHE_DIR")
    yt_crhoy_cache_db: str = Field(default=os.path.join("data", "crhoy", "youtube", "yt_crhoy_cache_db.json"), env="YT_CRHOY_CACHE_DB")
    url_link: str = Field(default="", env="URL_LINK")

    def get_telegram_operators(self) -> List[str]:
        return [x for x in self.telegram_operators.split(',')]
    
    def get_elevenlabs_api_keys(self) -> List[str]:
        return [x for x in self.elevenlabs_api_key.split(',')]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Allows extra fields in .env file without raising validation errors

# Create a single settings instance to be used throughout the application
settings = Settings()