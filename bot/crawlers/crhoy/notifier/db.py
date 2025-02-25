"""Database operations for the notifier bot."""

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from ..common.models import (
    CRHoyNews,
    CRHoyNotifierNews,
    CRHoySentNews,
    CRHoySummary
)


def delete_old_sent_news(session: Session, before_timestamp: datetime) -> None:
    """Delete records from crhoy_sent_news that are older than the given timestamp.
    
    This implements step 3 of the bot flow, clearing out old sent news records
    before the previous trigger time.
    
    Args:
        session: Database session
        before_timestamp: Delete records with timestamp before this time
    """
    stmt = delete(CRHoySentNews).where(CRHoySentNews.timestamp < before_timestamp)
    session.execute(stmt)
    session.commit()


def get_sent_news_ids(session: Session, after_timestamp: datetime) -> List[int]:
    """Get IDs of news that have been sent after the given timestamp.
    
    This implements step 4 of the bot flow, collecting IDs of news that were
    already sent in the current time window.
    
    Args:
        session: Database session
        after_timestamp: Get records with timestamp after or equal to this time
        
    Returns:
        List of news IDs that have been sent
    """
    stmt = select(CRHoySentNews.id).where(CRHoySentNews.timestamp >= after_timestamp)
    result = session.execute(stmt)
    return [row[0] for row in result]


def get_news_to_send(
    session: Session,
    after_timestamp: datetime,
    exclude_ids: Optional[List[int]] = None
) -> List[Tuple[int, datetime, str, str]]:
    """Get list of news that need to be sent, ordered by timestamp.
    
    This implements step 5 of the bot flow, collecting news that:
    - Have timestamp after or equal to the given time
    - Have been analyzed (exist in crhoy_notifier_news)
    - Were not skipped or failed in analysis
    - Have not been sent yet (not in exclude_ids)
    
    Args:
        session: Database session
        after_timestamp: Get news with timestamp after or equal to this time
        exclude_ids: List of news IDs to exclude (already sent)
        
    Returns:
        List of tuples (id, timestamp, url, smart_category) ordered by timestamp
    """
    # Build query joining notifier news with original news
    stmt = (
        select(
            CRHoyNotifierNews.id,
            CRHoyNotifierNews.timestamp,
            CRHoyNews.url,
            CRHoyNotifierNews.category
        )
        .join(CRHoyNews)
        .where(
            CRHoyNotifierNews.timestamp >= after_timestamp,
            CRHoyNotifierNews.skipped == False,  # noqa: E712
            CRHoyNotifierNews.failed == False    # noqa: E712
        )
        .order_by(CRHoyNotifierNews.timestamp)
    )
    
    # Add exclusion if IDs provided
    if exclude_ids:
        stmt = stmt.where(CRHoyNotifierNews.id.not_in(exclude_ids))
    
    result = session.execute(stmt)
    return list(result)


def get_summary_filename(
    session: Session,
    news_id: int,
    lang: str = 'ru'
) -> Optional[str]:
    """Get the filename of the summary for the given news ID and language.
    
    This implements part of step 7 of the bot flow, getting the path to the
    summary file.
    
    Args:
        session: Database session
        news_id: ID of the news article
        lang: Language code of the summary (defaults to 'ru' for Russian)
        
    Returns:
        Path to the summary file if it exists, None otherwise
    """
    stmt = (
        select(CRHoySummary.filename)
        .where(
            CRHoySummary.id == news_id,
            CRHoySummary.lang == lang
        )
    )
    result = session.execute(stmt).first()
    return result[0] if result else None 