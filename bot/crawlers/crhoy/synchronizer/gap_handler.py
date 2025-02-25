"""Gap handling functionality for CRHoy crawler."""

from datetime import date, timedelta
from typing import List, Optional, Set

from sqlalchemy import delete, select

from ..common.db import db_session
from ..common.logger import get_component_logger
from ..common.models import MissedCRHoyMetadata
from .updater import process_metadata_for_date

logger = get_component_logger("synchronizer.gap_handler")


class GapHandlerError(Exception):
    """Raised when gap handling fails."""
    pass


class DateRange:
    """Represents a date range for gap handling."""
    
    def __init__(self, start_date: date, end_date: date):
        """
        Initialize date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
        """
        if start_date > end_date:
            raise ValueError("start_date cannot be after end_date")
            
        self.start_date = start_date
        self.end_date = end_date
        
    def __iter__(self):
        """Iterate through dates in range."""
        current = self.start_date
        while current <= self.end_date:
            yield current
            current += timedelta(days=1)
            
    def __str__(self) -> str:
        """String representation of date range."""
        return f"{self.start_date} to {self.end_date}"
    
    def __eq__(self, other: object) -> bool:
        """Compare date ranges for equality."""
        if not isinstance(other, DateRange):
            return NotImplemented
        return (
            self.start_date == other.start_date and 
            self.end_date == other.end_date
        )


def get_earliest_gap() -> Optional[DateRange]:
    """
    Get the earliest gap from the database.
    
    PostgreSQL's daterange type uses [) notation (inclusive start, exclusive end).
    We convert it to our inclusive end date representation when creating the DateRange.
    
    Returns:
        DateRange if a gap exists, None otherwise
    """
    with db_session() as session:
        # Get the earliest gap record
        gap = session.execute(
            select(MissedCRHoyMetadata)
            .order_by(MissedCRHoyMetadata.gap)
            .limit(1)
        ).scalar_one_or_none()
        
        if gap:
            # Convert PostgreSQL's exclusive end to our inclusive end
            return DateRange(
                gap.gap.lower,  # type: ignore
                gap.gap.upper - timedelta(days=1)  # type: ignore
            )
        
        return None


def process_gap(gap: DateRange) -> bool:
    """
    Process a gap in metadata.
    
    This function follows the gaps handling flow:
    1. For each day in the gap:
       - Fetch and save metadata
       - Prepare DB updates
    2. If all metadata is received successfully:
       - Apply all DB updates
       - Remove the gap
       All in a single transaction
    
    Args:
        gap: Date range representing the gap
        
    Returns:
        True if gap was processed successfully, False otherwise
    """
    logger.info(f"Discovering metadata for gap {gap}")
    
    try:
        with db_session() as session:
            # Process each date in the gap
            updates_success = True
            for current_date in gap:
                success = process_metadata_for_date(
                    target_date=current_date,
                    session=session
                )
                if not success:
                    updates_success = False
                    break
            
            if not updates_success:
                logger.error(f"Failed to process some dates in gap {gap}")
                return False
            
            # Remove the gap record
            session.execute(
                delete(MissedCRHoyMetadata)
                .where(MissedCRHoyMetadata.gap.contains(gap.start_date))  # type: ignore
                .where(MissedCRHoyMetadata.gap.contains(gap.end_date))    # type: ignore
            )
            
            logger.info(f"Metadata for gap {gap} processed successfully")
            return True
            
    except Exception as e:
        logger.error(f"Error processing gap {gap}: {e}")
        return False


def construct_gaps(
    start_date: date,
    end_date: date,
    chunk_size: int
) -> List[DateRange]:
    """
    Construct gaps between two dates with specified chunk size.
    
    Args:
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        chunk_size: Maximum size of each gap
        
    Returns:
        List of DateRange objects
        
    Example:
        construct_gaps(date(2024,1,1), date(2024,1,7), 3) returns:
        [DateRange(2024-1-1, 2024-1-3), DateRange(2024-1-4, 2024-1-6), DateRange(2024-1-7, 2024-1-7)]
    """
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")
        
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
        
    gaps: List[DateRange] = []
    current = start_date
    
    while current <= end_date:
        # Calculate end of current chunk
        chunk_end = min(
            current + timedelta(days=chunk_size - 1),
            end_date
        )
        
        gaps.append(DateRange(current, chunk_end))
        current = chunk_end + timedelta(days=1)
        
    return gaps


def insert_gaps(gaps: List[DateRange]) -> None:
    """
    Insert gaps into the database.
    
    Args:
        gaps: List of date ranges to insert
    """
    try:
        with db_session() as session:
            for gap in gaps:
                # Create gap record
                gap_record = MissedCRHoyMetadata(
                    gap=f"[{gap.start_date},{gap.end_date}]"  # PostgreSQL daterange format
                )
                session.add(gap_record)
            
            # Remove explicit commit since db_session context manager will handle it
            logger.info(f"Inserted {len(gaps)} gaps into database")
            
    except Exception as e:
        logger.error(f"Failed to insert gaps: {e}")
        raise GapHandlerError(f"Failed to insert gaps: {e}")


def get_existing_gap_dates() -> Set[date]:
    """
    Get all dates that are currently part of any gap.
    
    Returns:
        Set of dates that are part of gaps
    """
    dates: Set[date] = set()
    
    with db_session() as session:
        # Get all gap records
        gaps = session.execute(
            select(MissedCRHoyMetadata)
        ).scalars().all()
        
        # Collect all dates from gaps
        for gap in gaps:
            current = gap.gap.lower  # type: ignore
            while current <= gap.gap.upper:  # type: ignore
                dates.add(current)
                current += timedelta(days=1)
                
    return dates
