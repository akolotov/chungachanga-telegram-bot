"""Data types for the notifier bot."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class NewsMessageData:
    """Data required to format and send a news message to Telegram.
    
    Fields:
        timestamp: Original news timestamp in Costa Rica timezone
        url: URL of the news article
        smart_category: Category from smart analysis (will be formatted as hashtag)
        summary: Summary of the news article
    """
    timestamp: datetime
    url: str
    smart_category: str
    summary: str 