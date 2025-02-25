"""Settings management for CRHoy crawler components."""

from datetime import date, time
from pathlib import Path
import json
from typing import Optional, Set, List, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from bot.types import LLMEngine

class CRHoyCrawlerSettings(BaseSettings):
    """Settings for CRHoy crawler components."""
    
    # Base directory for storing crawler data (metadata and news content)
    data_dir: Path = Field(
        default=Path("data/crhoy"),
        description="Base directory for storing crawler data",
        validation_alias="CRHOY_CRAWLER_DATA_DIR"
    )

    # Notifier settings
    notifier_trigger_times: List[time] = Field(
        default=[
            time(6, 0),   # 6:00
            time(12, 0),  # 12:00
            time(16, 30)  # 16:30
        ],
        description="List of times during the day when the notifier will be triggered",
        validation_alias="NEWS_NOTIFIER_TRIGGER_TIMES"
    )

    notifier_max_inactivity_interval: int = Field(
        default=300,  # 5 minutes
        description="Maximum time in seconds that the notifier can sleep without checking for trigger times",
        validation_alias="NEWS_NOTIFIER_MAX_INACTIVITY_INTERVAL",
        gt=0
    )

    # Telegram notifier bot settings
    notifier_telegram_bot_token: str = Field(
        default="",
        description="Telegram Bot Token for the news notifier",
        validation_alias="NEWS_NOTIFIER_TELEGRAM_BOT_TOKEN"
    )

    notifier_telegram_channel_id: str = Field(
        default="",
        description="Telegram channel ID where the bot will post news summaries",
        validation_alias="NEWS_NOTIFIER_TELEGRAM_CHANNEL_ID"
    )

    notifier_telegram_max_retries: int = Field(
        default=3,
        description="Maximum number of retries for sending messages to Telegram",
        validation_alias="NEWS_NOTIFIER_TELEGRAM_MAX_RETRIES",
        gt=0
    )

    notifier_telegram_messages_delay: float = Field(
        default=1.0,
        description="Delay in seconds between sending messages to Telegram to avoid rate limits",
        validation_alias="NEWS_NOTIFIER_TELEGRAM_MESSAGES_DELAY",
        gt=0
    )

    # Database connection
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/crhoy",
        description="PostgreSQL database URL",
        validation_alias="CRHOY_CRAWLER_DATABASE_URL"
    )

    # Synchronizer settings
    first_day: Optional[date] = Field(
        default=None,
        description="First day from which to start synchronizing metadata",
        validation_alias="CRHOY_CRAWLER_FIRST_DAY"
    )

    check_updates_interval: int = Field(
        default=300,  # 5 minutes
        description="Interval in seconds between metadata update checks",
        validation_alias="CRHOY_CRAWLER_CHECK_UPDATES_INTERVAL",
        gt=0
    )

    days_chunk_size: int = Field(
        default=5,
        description="Number of days to process in one metadata update iteration",
        validation_alias="CRHOY_CRAWLER_DAYS_CHUNK_SIZE",
        gt=0
    )

    # Downloader settings
    download_interval: int = Field(
        default=60,  # 1 minute
        description="Interval in seconds between news download attempts",
        validation_alias="CRHOY_CRAWLER_DOWNLOAD_INTERVAL",
        gt=0
    )

    downloads_chunk_size: int = Field(
        default=10,
        description="Number of news articles to download in one iteration",
        validation_alias="CRHOY_CRAWLER_DOWNLOADS_CHUNK_SIZE",
        gt=0
    )

    ignore_categories: Set[str] = Field(
        default_factory=set,
        description="Categories of news to ignore (not download)",
        validation_alias="CRHOY_CRAWLER_IGNORE_CATEGORIES"
    )

    # HTTP client settings
    request_timeout: float = Field(
        default=30.0,
        description="Timeout in seconds for HTTP requests",
        validation_alias="CRHOY_CRAWLER_REQUEST_TIMEOUT",
        gt=0
    )

    max_retries: int = Field(
        default=3,
        description="Maximum number of retries for failed HTTP requests",
        validation_alias="CRHOY_CRAWLER_MAX_RETRIES",
        ge=0
    )

    agent_engine: LLMEngine = Field(
        default=LLMEngine.GEMINI,
        description="LLM engine to use for agent operations",
        validation_alias="AGENT_ENGINE"
    )

    agent_engine_api_key: str = Field(
        default="",
        description="API key for the LLM engine",
        validation_alias="AGENT_ENGINE_API_KEY"
    )

    agent_engine_basic_model: str = Field(
        default="gemini-2.0-flash",
        description="Basic model to use for the LLM engine",
        validation_alias="AGENT_ENGINE_BASIC_MODEL"
    )

    agent_engine_basic_model_request_limit: int = Field(
        default=10,
        description="Request limit for the basic model",
        validation_alias="AGENT_ENGINE_BASIC_MODEL_REQUEST_LIMIT",
        gt=0
    )

    agent_engine_basic_model_request_limit_period_seconds: int = Field(
        default=60,
        description="Time window (in seconds) after which the request limit for the basic model are applied",
        validation_alias="AGENT_ENGINE_BASIC_MODEL_REQUEST_LIMIT_PERIOD_SECONDS",
        gt=0
    )

    agent_engine_light_model: str = Field(
        default="gemini-2.0-flash-lite-preview-02-05",
        description="Lightweight model to use for the LLM engine",
        validation_alias="AGENT_ENGINE_LIGHT_MODEL"
    )

    agent_engine_light_model_request_limit: int = Field(
        default=10,
        description="Request limit for the lightweight model",
        validation_alias="AGENT_ENGINE_LIGHT_MODEL_REQUEST_LIMIT",
        gt=0
    )

    agent_engine_light_model_request_limit_period_seconds: int = Field(
        default=60,
        description="Time window (in seconds) after which the request limit for the lightweight model are applied",
        validation_alias="AGENT_ENGINE_LIGHT_MODEL_REQUEST_LIMIT_PERIOD_SECONDS",
        gt=0
    )

    keep_raw_engine_responses: bool = Field(
        default=False,
        description="Whether to keep raw engine responses",
        validation_alias="KEEP_RAW_ENGINE_RESPONSES"
    )

    raw_engine_responses_dir: Path = Field(
        default=Path("data/crhoy/llm/responses"),
        description="Directory to store raw engine responses",
        validation_alias="RAW_ENGINE_RESPONSES_DIR"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        validate_default=True,
        extra = "ignore"  # Allows extra fields in .env file without raising validation errors        
    )

    @field_validator("ignore_categories", mode="before")
    def parse_ignore_categories(cls, v: Union[str, Set[str]]) -> Set[str]:
        """Parse comma-separated string of categories into a set."""
        if isinstance(v, str):
            return {cat.strip() for cat in v.split(",") if cat.strip()}
        return v

    @field_validator("first_day", mode="before")
    def parse_first_day(cls, v: Union[str, None, date]) -> Optional[date]:
        """Parse date string into date object."""
        if isinstance(v, str):
            try:
                year, month, day = map(int, v.split("-"))
                return date(year, month, day)
            except (ValueError, TypeError):
                raise ValueError("first_day must be in YYYY-MM-DD format")
        return v

    @field_validator("data_dir", mode="before")
    def parse_data_dir(cls, v: Union[str, Path]) -> Path:
        """Convert string path to Path object."""
        return Path(v) if isinstance(v, str) else v

    @field_validator("notifier_trigger_times", mode="before")
    def parse_trigger_times(cls, v: Union[str, List[time]]) -> List[time]:
        """Parse JSON string of trigger times into a list of time objects.
        
        The times are assumed to be in Costa Rica timezone (America/Costa_Rica).
        Input format examples:
        - JSON array of HH:MM strings: '["06:00", "12:00", "16:30"]'
        - List of time objects (when set programmatically)
        """
        if isinstance(v, str):
            try:
                # Parse JSON string into list of time strings
                time_strings = json.loads(v)
                if not isinstance(time_strings, list):
                    raise ValueError("Trigger times must be a JSON array")
                
                # Convert each time string to time object
                # Note: time objects are naive (no timezone), but we document
                # that they are assumed to be in Costa Rica timezone
                return [
                    time.fromisoformat(t) if isinstance(t, str) else t
                    for t in time_strings
                ]
            except (json.JSONDecodeError, ValueError) as e:
                raise ValueError(
                    f"Invalid trigger times format. Must be a JSON array of "
                    f"time strings in HH:MM format (Costa Rica timezone): {str(e)}"
                )
        return v


# Create a global settings instance
settings = CRHoyCrawlerSettings()