"""Telegram message formatting and sending functionality."""

import asyncio
from datetime import datetime
import re
from typing import Optional

from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

from ..settings import settings
from ..common.logger import get_component_logger
from .types import NewsMessageData
from ..common.constants import COSTA_RICA_TIMEZONE
from ..common.utils import ensure_costa_rica_timezone


logger = get_component_logger("notifier.sender")


def escape_markdown_v2(text: str, exclude_hashtag: bool = False) -> str:
    """Escape special characters for Telegram's MarkdownV2 format.
    
    Args:
        text: Text to escape
        exclude_hashtag: If True, don't escape # character (for hashtags)
        
    Returns:
        Text with special characters escaped
    """
    # Characters that need to be escaped in MarkdownV2
    special_chars = r'_*[]()~`>+-=|{}.!'
    if not exclude_hashtag:
        special_chars += '#'
    
    # Escape each special character with a backslash
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    
    return text


def format_news_message(news: NewsMessageData) -> str:
    """Format news data into a Telegram message according to the required format.
    
    Args:
        news: News data to format
        
    Returns:
        Formatted message string in the format:
        _YYYY/MM/DD HH:MM_  # Italic timestamp in Costa Rica timezone
        
        {summary}
        
        {url}
        #{parent_category} #{child_category}  # if category has parent/child
        #{category}  # if category is single-level
    """
    # Ensure timestamp is in Costa Rica timezone
    timestamp = ensure_costa_rica_timezone(news.timestamp)
    
    # Format timestamp in Costa Rica time
    # Escape special chars first, then wrap in italic markers
    timestamp_str = f"_{escape_markdown_v2(timestamp.strftime('%Y/%m/%d %H:%M'))}_"
    
    # Escape summary and URL
    summary = escape_markdown_v2(news.summary)
    url = escape_markdown_v2(news.url)
    
    # Format category as hashtag(s)
    if '/' in news.smart_category:
        parent, child = news.smart_category.split('/', 1)
        # Escape category names but preserve # by escaping it manually
        hashtags = f"\\#{escape_markdown_v2(parent)} \\#{escape_markdown_v2(child)}"
    else:
        hashtags = f"\\#{escape_markdown_v2(news.smart_category)}"
    
    # Combine all parts with required spacing
    return f"{timestamp_str}\n\n{summary}\n\n{url}\n\n{hashtags}"


async def send_news_message(
    bot: Bot,
    news: NewsMessageData,
    max_retries: Optional[int] = None
) -> bool:
    """Send a news message to the configured Telegram channel with retries.
    
    Args:
        bot: Initialized Telegram bot instance
        news: News data to send
        max_retries: Maximum number of retries, defaults to NEWS_NOTIFIER_TELEGRAM_MAX_RETRIES
        
    Returns:
        True if message was sent successfully, False if all retries failed
        
    Note:
        Uses disable_web_page_preview=True as required
    """
    if max_retries is None:
        max_retries = settings.notifier_telegram_max_retries
        
    message = format_news_message(news)
    attempt = 0
    
    while attempt <= max_retries:
        try:
            await bot.send_message(
                chat_id=settings.notifier_telegram_channel_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN_V2,  # No special formatting - plain text
                disable_web_page_preview=True
            )
            return True
            
        except TelegramError as e:
            attempt += 1
            if attempt > max_retries:
                logger.error(
                    "Failed to send news message after %d attempts. Error: %s",
                    max_retries + 1, str(e)
                )
                return False
                
            # Log warning and retry
            logger.warning(
                "Failed to send news message (attempt %d/%d). Error: %s. Retrying...",
                attempt, max_retries + 1, str(e)
            )
            # Wait briefly before retry
            await asyncio.sleep(1)


if __name__ == "__main__":
    # Test message sending with a sample news article
    test_timestamp = datetime.now(COSTA_RICA_TIMEZONE)
    test_summary = """В четверг Коста-риканский институт электричества (ICE) объявил о снижении тарифов на электроэнергию. 
    Снижение составит в среднем 8.5% для жилых помещений и будет действовать с апреля по декабрь 2025 года."""
    
    # Test both single category and parent/child category formats
    test_cases = [
        NewsMessageData(
            timestamp=test_timestamp,
            url="https://www.crhoy.com/economia/ice-anuncia-rebaja-en-tarifas-electricas",
            smart_category="economia",
            summary=test_summary
        ),
        NewsMessageData(
            timestamp=test_timestamp,
            url="https://www.crhoy.com/deportes/futbol/saprissa-gana-el-clasico",
            smart_category="deportes/futbol",
            summary=test_summary
        )
    ]
    
    print("\nTesting message formatting:")
    for case in test_cases:
        print("\nTest case:")
        print(f"Category: {case.smart_category}")
        print("\nFormatted message:")
        print("=" * 40)
        print(format_news_message(case))
        print("=" * 40)
    
    # Test actual sending if bot token is configured
    if settings.notifier_telegram_bot_token:
        print("\nTesting message sending to channel...")
        asyncio.run(send_news_message(
            Bot(token=settings.notifier_telegram_bot_token),
            test_cases[1]  # Send the economia test case
        ))
    else:
        print("\nSkipping message sending test - no bot token configured") 