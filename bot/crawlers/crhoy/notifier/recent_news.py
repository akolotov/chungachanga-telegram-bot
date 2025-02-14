"""Core notifier flow implementation."""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session
from telegram import Bot

from ..common.logger import get_component_logger
from ..common.utils import TriggerTimeInfo, get_trigger_time_info
from ..common.db import db_session, init_db
from ..common.models import CRHoySentNews
from ..settings import settings
from .db import (
    delete_old_sent_news,
    get_sent_news_ids,
    get_news_to_send,
    get_summary_filename
)
from .telegram import NewsMessageData, send_news_message
from ..common.constants import COSTA_RICA_TIMEZONE


logger = get_component_logger("notifier.recent")


async def process_news_batch(
    bot: Bot,
    session: Session,
    trigger_info: TriggerTimeInfo,
    dry_run: bool = False
) -> None:
    """Process a batch of news for the current trigger time.
    
    This implements steps 2-12 of the bot flow:
    2. Get trigger time info
    3. Delete old sent news records
    4. Get list of already sent news IDs
    5. Get list of news to send
    6-12. Process each news article
    
    Args:
        bot: Initialized Telegram bot instance
        session: Database session
        trigger_info: Information about current trigger time window
        dry_run: If True, don't update database or send messages
    """
    now = datetime.now(COSTA_RICA_TIMEZONE)
    
    # Shift the previous time back by 2 * CHECK_UPDATES_INTERVAL to account for
    # async nature of synchronizer and downloader
    shifted_previous = trigger_info.previous - timedelta(
        seconds=2 * settings.check_updates_interval
    )
    
    logger.info(
        "Processing news batch from %s (shifted from %s) up to current time %s",
        shifted_previous.isoformat(),
        trigger_info.previous.isoformat(),
        now.isoformat()
    )
    
    # Step 3: Delete old sent news records
    if not dry_run:
        delete_old_sent_news(session, shifted_previous)
        logger.info("Deleted old sent news records before %s", shifted_previous)
    
    # Step 4: Get list of already sent news IDs
    sent_ids = get_sent_news_ids(session, shifted_previous)
    logger.info("Found %d already sent news in current window", len(sent_ids))
    
    # Step 5: Get list of news to send
    news_to_send = get_news_to_send(session, shifted_previous, sent_ids)
    logger.info("Found %d news to send", len(news_to_send))
    
    # Steps 6-12: Process each news article
    for news_id, timestamp, url, smart_category in news_to_send:
        # Record start time of processing this news
        start_time = datetime.now(COSTA_RICA_TIMEZONE)
        
        # Step 7: Get Russian summary
        summary_file = get_summary_filename(session, news_id)
        if summary_file is None:
            logger.warning("No Russian summary found for news %d, skipping", news_id)
            continue
            
        try:
            summary = Path(summary_file).read_text(encoding='utf-8').strip()
        except (IOError, UnicodeError) as e:
            logger.error(
                "Failed to read summary file %s for news %d: %s",
                summary_file, news_id, str(e)
            )
            continue
        
        # Steps 8-9: Format and send message
        news_data = NewsMessageData(
            timestamp=timestamp,
            url=url,
            smart_category=smart_category,
            summary=summary
        )
        
        if dry_run:
            logger.info(
                "Would send news %d:\n%s\n%s\n%s\n#%s",
                news_id, timestamp, summary, url, smart_category
            )
            continue
            
        success = await send_news_message(bot, news_data)
        
        # Step 10: Update sent news if successful
        if success:
            session.add(CRHoySentNews(id=news_id, timestamp=timestamp))
            session.commit()
            logger.info("Successfully sent and recorded news %d", news_id)
        
        # Step 11: Calculate remaining delay accounting for processing time
        elapsed = (datetime.now(COSTA_RICA_TIMEZONE) - start_time).total_seconds()
        remaining_delay = max(0.0, settings.notifier_telegram_messages_delay - elapsed)
        
        if remaining_delay > 0:
            logger.debug(
                "Waiting %.1f seconds before next message (%.1f seconds elapsed)",
                remaining_delay, elapsed
            )
            await asyncio.sleep(remaining_delay)


async def process_recent_news(
    bot: Bot,
    current_time: Optional[datetime] = None,
    dry_run: bool = False
) -> None:
    """Run the main bot flow starting from step 2.
    
    Args:
        bot: Initialized Telegram bot instance
        current_time: Override current time for testing
        dry_run: If True, don't update database or send messages
    """
    # Step 2: Get trigger time info
    trigger_info = get_trigger_time_info(current_time)
    
    with db_session() as session:
        await process_news_batch(bot, session, trigger_info, dry_run)


if __name__ == "__main__":
    # Initialize database
    init_db(settings.database_url)
    
    # Test with a specific time
    test_time = datetime.now(COSTA_RICA_TIMEZONE)
    print(f"\nTesting recent news notification in dry run mode at {test_time}")
    
    # Create test bot with dummy token
    test_bot = Bot(token="dummy_token")
    
    # Process recent news
    asyncio.run(process_recent_news(bot=test_bot, current_time=test_time, dry_run=True)) 