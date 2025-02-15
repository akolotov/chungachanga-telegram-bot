"""News downloading and processing functionality for CRHoy crawler."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Set, Tuple, Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..common.db import db_session
from ..common.logger import get_component_logger
from ..common.models import CRHoyNews, CRHoyNewsCategories
from ..common.constants import CRHOY_REQUEST_HEADERS
from ..common.utils import get_trigger_time_info
from ..settings import settings
from bot.web_parsers.crhoy import parse_article
from bot.web_parsers.helper import WebDownloadError, WebParserError
from .news_analyzer import analyze_news, NewsAnalyzerError

logger = get_component_logger("downloader.processor")


class NewsProcessorError(Exception):
    """Raised when news processing fails."""
    pass


def _get_news_to_process(
    session: Session,
    chunk_size: int
) -> List[CRHoyNews]:
    """
    Get a chunk of unprocessed news that should be downloaded.
    Combines two sets of records:
    1. Most recent unprocessed news within current notification window
    2. Older unprocessed news in reverse chronological order

    Args:
        session: Database session
        chunk_size: Maximum number of news to return

    Returns:
        List of news entries to process, ordered by timestamp
        (older to newer for recent news, newer to older for old news)
    """
    # Get trigger time info to determine the window for recent news
    trigger_info = get_trigger_time_info()

    # Query for recent unprocessed news (within notification window)
    recent_query = (
        select(CRHoyNews)
        .where(CRHoyNews.filename == "")
        .where(CRHoyNews.skipped == False)  # noqa: E712
        .where(CRHoyNews.failed == False)   # noqa: E712
        .where(CRHoyNews.timestamp >= trigger_info.shifted_previous)
        .order_by(CRHoyNews.timestamp)  # Oldest first for recent news
        .limit(chunk_size)
    )
    recent_news = list(session.execute(recent_query).scalars().all())

    # If we have capacity for more news, get older news in reverse order
    remaining_capacity = chunk_size - len(recent_news)
    if remaining_capacity > 0:
        older_query = (
            select(CRHoyNews)
            .where(CRHoyNews.filename == "")
            .where(CRHoyNews.skipped == False)  # noqa: E712
            .where(CRHoyNews.failed == False)   # noqa: E712
            .where(CRHoyNews.timestamp < trigger_info.shifted_previous)
            .order_by(CRHoyNews.timestamp.desc())  # Newest first for older news
            .limit(remaining_capacity)
        )
        older_news = list(session.execute(older_query).scalars().all())
    else:
        older_news = []

    # Combine both lists - recent news first (ordered old to new),
    # then older news (ordered new to old)
    return recent_news + older_news


def _get_news_categories(
    session: Session,
    news_ids: List[int]
) -> Dict[int, str]:
    """
    Get categories for all news IDs in a single query.

    Args:
        session: Database session
        news_ids: List of news IDs to get categories for

    Returns:
        Dictionary mapping news ID to category path
    """
    query = (
        select(CRHoyNewsCategories.news_id, CRHoyNewsCategories.category)
        .where(CRHoyNewsCategories.news_id.in_(news_ids))
    )

    return {
        row.news_id: row.category
        for row in session.execute(query).all()
    }


def _prepare_news_path(news: CRHoyNews) -> Path:
    """
    Prepare path for saving news content.

    Args:
        news: News entry to prepare path for

    Returns:
        Path where news content should be saved
    """
    # Convert timestamp to components
    dt = news.timestamp.astimezone()  # Use news timezone
    date_str = dt.strftime("%Y-%m-%d")
    time_str = dt.strftime("%H-%M")

    # Construct path
    return (
        settings.data_dir / "news" /
        date_str /
        f"{time_str}-{news.id}.md"
    )


def _save_news_content(
    path: Path,
    title: str,
    content: str
) -> None:
    """
    Save news content to file.

    Args:
        path: Path where to save the content
        title: News title
        content: News content

    Raises:
        NewsProcessorError: If saving fails
    """
    try:
        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Save content
        with path.open('w', encoding='utf-8') as f:
            f.write(f"--- title: {title}\n\n")
            f.write(content)

        logger.info(f"Saved news content to {path}")

    except Exception as e:
        raise NewsProcessorError(f"Failed to save news content to {path}: {e}")


def process_news(news: CRHoyNews) -> Optional[str]:
    """
    Process a single news entry.

    This function:
    1. Downloads and parses the news page
    2. Saves the content to a file
    3. Returns the path where content was saved

    Args:
        news: News entry to process

    Returns:
        Path where content was saved if successful, None if failed

    Raises:
        NewsProcessorError: If processing fails unexpectedly
    """
    try:
        # Download and parse news
        title, content = parse_article(
            news.url,
            CRHOY_REQUEST_HEADERS
        )

        if not title or not content:
            logger.error(
                f"Failed to parse news {news.id}: empty title or content")
            return None

        # Prepare path and save content
        path = _prepare_news_path(news)
        _save_news_content(path, title, content)

        return str(path)

    except WebDownloadError as e:
        logger.error(f"Failed to download news {news.id}: {e}")
        return None

    except WebParserError as e:
        logger.error(f"Failed to parse news {news.id}: {e}")
        return None

    except Exception as e:
        logger.error(f"Unexpected error processing news {news.id}: {e}")
        raise NewsProcessorError(f"Failed to process news: {e}")


def process_news_chunk() -> None:
    """
    Process a chunk of news.

    This function implements the main news processing flow:
    1. Get chunk of unprocessed news
    2. Get categories for all news in chunk in a single query
    3. For each news:
       - Check if category is in ignore list
       - If yes, mark as skipped
       - If no, try to download and parse
       - If parsing fails, mark as failed
       - If parsing succeeds, update filename
       - Commit changes for this news
       - If news was processed successfully, analyze it
       Each news is processed in its own transaction
    """
    try:
        with db_session() as session:
            # Get news to process without category filtering
            news_chunk = _get_news_to_process(
                session,
                settings.downloads_chunk_size
            )

            if not news_chunk:
                logger.info("No news to process")
                return

            # Get categories for all news in a single query
            news_categories = _get_news_categories(
                session,
                [news.id for news in news_chunk]
            )

            logger.info(f"Processing {len(news_chunk)} news entries")

            # Process each news in its own transaction
            for news in news_chunk:
                try:
                    # Check if category should be ignored
                    category = news_categories.get(news.id)
                    if category and category in settings.ignore_categories:
                        logger.info(
                            f"Marking news {news.id} as skipped due to "
                            f"ignored category {category}"
                        )
                        news.skipped = True
                    else:
                        # Try to process the news
                        path = process_news(news)
                        if path:
                            # Success - update filename
                            news.filename = path
                        else:
                            # Failed to parse - mark as failed
                            news.failed = True

                            # To receive the news that failed to parse:
                            # SELECT n.id, n.url, n.timestamp, c.category
                            # FROM crhoy_news n
                            # JOIN crhoy_news_categories c ON n.id = c.news_id
                            # WHERE n.failed = true
                            # ORDER BY n.timestamp DESC;

                    # Commit changes for this news
                    session.commit()

                    # If news was processed successfully, analyze it
                    if news.filename:
                        try:
                            analyze_news(news, session)
                        except NewsAnalyzerError as e:
                            logger.error(
                                f"Failed to analyze news {news.id}: {e}")
                            # Continue with next news even if analysis fails

                except Exception as e:
                    logger.error(f"Failed to process news {news.id}: {e}")
                    # Mark as failed and continue with next
                    news.failed = True
                    session.commit()

    except Exception as e:
        logger.error(f"Error in news processing: {e}")
        raise NewsProcessorError(f"News processing failed: {e}")
