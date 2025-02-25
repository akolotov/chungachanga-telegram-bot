"""Metadata update functionality for CRHoy crawler."""

from datetime import date
from pathlib import Path
from typing import Dict, List, Set, Tuple, Union, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..common.api_client import fetch_news_metadata, CRHoyAPIError
from ..common.constants import SPANISH_MONTH_MAP, COSTA_RICA_UTC_OFFSET
from ..common.db import db_session
from ..common.file_manager import save_metadata, FileManagerError
from ..common.logger import get_component_logger
from ..common.models import (
    CRHoyNews,
    CRHoyCategoriesCatalog,
    CRHoyNewsCategories,
    CRHoyMetadata,
)
from ..settings import settings

logger = get_component_logger("synchronizer.updater")


class MetadataUpdateError(Exception):
    """Raised when metadata update fails."""
    pass


def _build_category_path(categories: List[List[Union[str, int]]]) -> str:
    """
    Build category path from metadata categories list.
    
    Args:
        categories: List of category entries from metadata
        
    Returns:
        Category path string (e.g., "deportes/futbol")
    """
    # Extract URL-compatible category names (second element) and join with "/"
    return "/".join(cat[1] for cat in categories)


def _parse_timestamp(news_date: str, news_hour: str) -> str:
    """
    Parse timestamp from metadata date and hour.
    
    Args:
        news_date: Date string from metadata (e.g., "Febrero 6, 2025")
        news_hour: Hour string from metadata (e.g., " 9:01 am ")
        
    Returns:
        Timestamp string in format "YYYY-MM-DD HH:MM:SS-06" (Costa Rica timezone)
    """
    # Parse date
    parts = news_date.lower().replace(",", "").split()
    month = SPANISH_MONTH_MAP[parts[0]]
    day = parts[1].zfill(2)
    year = parts[2]
    
    # Parse hour (convert to 24-hour format)
    hour = news_hour.strip()
    is_pm = "pm" in hour.lower()
    hour = hour.lower().replace("am", "").replace("pm", "").strip()
    hour, minute = map(int, hour.split(":"))
    
    if is_pm and hour != 12:
        hour += 12
    elif not is_pm and hour == 12:
        hour = 0
        
    # Format timestamp with Costa Rica timezone
    return f"{year}-{month}-{day} {hour:02d}:{minute:02d}:00{COSTA_RICA_UTC_OFFSET}"


def _get_new_news_ids(
    session: Session, metadata: Dict
) -> Set[int]:
    """
    Get IDs of news that don't exist in the database.
    
    Args:
        session: Database session
        metadata: News metadata dictionary
        
    Returns:
        Set of new news IDs
    """
    # Extract all news IDs from metadata
    metadata_ids = {news["id"] for news in metadata["ultimas"]}
    
    # Get existing IDs from database
    existing_ids = {
        id_[0] for id_ in 
        session.execute(
            select(CRHoyNews.id).where(CRHoyNews.id.in_(metadata_ids))
        ).all()
    }
    
    # Return IDs that don't exist in database
    return metadata_ids - existing_ids


def _prepare_db_updates(
    metadata: Dict,
    new_ids: Set[int]
) -> Tuple[List[CRHoyNews], Set[str], List[CRHoyNewsCategories]]:
    """
    Prepare database updates for new news entries.
    
    Args:
        metadata: News metadata dictionary
        new_ids: Set of new news IDs
        
    Returns:
        Tuple containing:
        - List of news entries to add
        - Set of new categories to add
        - List of news-category relationships to add
    """
    news_entries: List[CRHoyNews] = []
    new_categories: Set[str] = set()  # Set of unique category paths
    news_categories: List[CRHoyNewsCategories] = []
    
    # Process each new news entry
    for news in metadata["ultimas"]:
        if news["id"] not in new_ids:
            continue
            
        # Build category path
        category_path = _build_category_path(news["categories"])
        
        # Add to new categories set
        new_categories.add(category_path)
            
        # Create news entry
        news_entry = CRHoyNews(
            id=news["id"],
            url=news["url"],
            timestamp=_parse_timestamp(news["date"], news["hour"]),
            filename="",  # Will be set by downloader
            skipped=False,
            failed=False
        )
        news_entries.append(news_entry)
        
        # Create news-category relationship
        news_category = CRHoyNewsCategories(
            news_id=news["id"],
            category=category_path
        )
        news_categories.append(news_category)
    
    return news_entries, new_categories, news_categories


def process_metadata_for_date(
    target_date: date,
    session: Session,
    metadata: Optional[Dict] = None,
    metadata_path: Optional[Path] = None
) -> bool:
    """
    Process metadata for a specific date and prepare DB updates.
    This function doesn't commit changes - it's up to the caller to manage the transaction.
    
    Args:
        target_date: Date to process metadata for
        session: Database session to use
        metadata: Optional pre-fetched metadata (if None, will be fetched)
        metadata_path: Optional pre-saved metadata path (if None, will be saved)
        
    Returns:
        True if processing was successful, False otherwise
        
    Raises:
        MetadataUpdateError: If processing fails
    """
    try:
        # Fetch and save metadata if not provided
        if metadata is None:
            metadata = fetch_news_metadata(
                target_date,
                timeout=settings.request_timeout,
                retries=settings.max_retries
            )
        
        if metadata_path is None:
            metadata_path = save_metadata(settings.data_dir, target_date, metadata)
        
        # Get new news IDs
        new_ids = _get_new_news_ids(session, metadata)
        
        if not new_ids:
            logger.info(f"No new news found for {target_date}")
            
            # Still mark the date as processed
            session.merge(CRHoyMetadata(
                date=target_date,
                path=str(metadata_path)
            ))
            
            return True
            
        # Prepare database updates
        news_entries, new_categories, news_categories = _prepare_db_updates(
            metadata, new_ids
        )
        
        # Get existing categories
        existing_categories = {
            cat.category: cat for cat in
            session.execute(
                select(CRHoyCategoriesCatalog)
                .where(CRHoyCategoriesCatalog.category.in_(new_categories))
            ).scalars().all()
        }
        
        # Add new categories
        for category_path in new_categories:
            if category_path not in existing_categories:
                cat = CRHoyCategoriesCatalog(
                    category=category_path
                )
                session.add(cat)
        
        # Add news entries and relationships
        session.add_all(news_entries)
        session.add_all(news_categories)
        
        # Mark date as processed
        session.merge(CRHoyMetadata(
            date=target_date,
            path=str(metadata_path)
        ))
        
        logger.info(
            f"Added {len(news_entries)} news entries and "
            f"{len(new_categories) - len(existing_categories)} new categories for {target_date}"
        )
        
        return True
            
    except (CRHoyAPIError, FileManagerError) as e:
        logger.error(f"Failed to fetch or save metadata for {target_date}: {e}")
        return False
        
    except Exception as e:
        logger.error(f"Unexpected error processing metadata for {target_date}: {e}")
        raise MetadataUpdateError(f"Failed to process metadata: {e}")


def update_metadata_for_date(target_date: date) -> bool:
    """
    Update metadata for a specific date. This function manages its own transaction.
    Use process_metadata_for_date() if you need to manage the transaction yourself.
    
    Args:
        target_date: Date to update metadata for
        
    Returns:
        True if update was successful, False otherwise
        
    Raises:
        MetadataUpdateError: If update fails
    """
    with db_session() as session:
        return process_metadata_for_date(target_date, session)
