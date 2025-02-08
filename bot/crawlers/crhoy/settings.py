"""Settings management for CRHoy crawler components."""

from datetime import date
from pathlib import Path
from typing import Optional, Set

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CRHoyCrawlerSettings(BaseSettings):
    """Settings for CRHoy crawler components."""
    
    # Base directory for storing crawler data (metadata and news content)
    data_dir: Path = Field(
        default=Path("data/crhoy"),
        description="Base directory for storing crawler data",
        validation_alias="CRHOY_CRAWLER_DATA_DIR"
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

    user_agent: str = Field(
        default="CRHoy Crawler/1.0",
        description="User agent string for HTTP requests",
        validation_alias="CRHOY_CRAWLER_USER_AGENT"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        validate_default=True,
        extra = "ignore"  # Allows extra fields in .env file without raising validation errors        
    )

    @field_validator("ignore_categories", mode="before")
    def parse_ignore_categories(cls, v: str | Set[str]) -> Set[str]:
        """Parse comma-separated string of categories into a set."""
        if isinstance(v, str):
            return {cat.strip() for cat in v.split(",") if cat.strip()}
        return v

    @field_validator("first_day", mode="before")
    def parse_first_day(cls, v: str | None | date) -> Optional[date]:
        """Parse date string into date object."""
        if isinstance(v, str):
            try:
                year, month, day = map(int, v.split("-"))
                return date(year, month, day)
            except (ValueError, TypeError):
                raise ValueError("first_day must be in YYYY-MM-DD format")
        return v

    @field_validator("data_dir", mode="before")
    def parse_data_dir(cls, v: str | Path) -> Path:
        """Convert string path to Path object."""
        return Path(v) if isinstance(v, str) else v


# Create a global settings instance
settings = CRHoyCrawlerSettings()