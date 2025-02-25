"""Scheduling functionality for CRHoy metadata synchronizer."""

from datetime import date, datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy import select, func

from ..common.api_client import (
    check_internet_connection,
    check_api_availability
)
from ..common.constants import COSTA_RICA_TIMEZONE
from ..common.db import db_session
from ..common.logger import get_component_logger
from ..common.models import CRHoyMetadata
from ..common.state import state
from ..common.utils import sleep_until_next_check
from ..settings import settings
from .gap_handler import get_earliest_gap, process_gap, construct_gaps, insert_gaps
from .updater import update_metadata_for_date

logger = get_component_logger("synchronizer.scheduler")


def get_costa_rica_now() -> datetime:
    """Get current datetime in Costa Rica timezone."""
    return datetime.now(COSTA_RICA_TIMEZONE)


def get_costa_rica_today() -> date:
    """Get current date in Costa Rica timezone."""
    return get_costa_rica_now().date()


def check_connectivity(timeout: float = 5.0) -> bool:
    """
    Check if both internet and CRHoy API are available.
    
    Args:
        timeout: Timeout for connectivity checks in seconds
        
    Returns:
        True if both internet and API are available
    """
    if not check_internet_connection(timeout):
        logger.warning("No internet connection available")
        return False
        
    if not check_api_availability(timeout):
        logger.warning("CRHoy API is not available")
        return False
        
    return True


def get_db_date_range() -> Tuple[Optional[date], Optional[date]]:
    """
    Get the oldest and latest dates from metadata table.
    
    Returns:
        Tuple of (oldest_date, latest_date), either can be None if no records
    """
    with db_session() as session:
        result = session.execute(
            select(
                func.min(CRHoyMetadata.date),
                func.max(CRHoyMetadata.date)
            )
        ).first()
        
        return result[0], result[1] if result else (None, None)


def handle_initial_gaps() -> None:
    """
    Handle initial gaps based on FIRST_DAY setting.
    This should be called once at startup.
    
    This function implements the initial gap identification logic:
    1. Get the oldest date from metadata table
    2. If FIRST_DAY is set and oldest date > FIRST_DAY:
       - Create gaps from FIRST_DAY to the day before oldest_date
    """
    if not settings.first_day:
        return
        
    oldest_date, _ = get_db_date_range()
    if oldest_date and settings.first_day < oldest_date:
        # Create gaps from FIRST_DAY to the day before oldest_date
        gaps = construct_gaps(
            start_date=settings.first_day,
            end_date=oldest_date - timedelta(days=1),
            chunk_size=settings.days_chunk_size
        )
        insert_gaps(gaps)
        logger.info(
            f"Inserted historical gaps from {settings.first_day} "
            f"to {oldest_date - timedelta(days=1)}"
        )


def handle_day_switch(current_date: date) -> None:
    """
    Handle day switch by checking for gaps and inserting them if needed.
    
    This function implements the gap identification logic for day switches:
    1. Get the latest date from metadata table
    2. If exists, create gap from that date to yesterday (inclusive)
    
    Args:
        current_date: Current date in Costa Rica timezone
    """
    _, latest_date = get_db_date_range()
    
    # If we have previous records, check for gaps
    if latest_date:
        # Create gap from latest date to yesterday (inclusive)
        # We include latest_date because we need to ensure we have its final version
        yesterday = current_date - timedelta(days=1)
        if latest_date <= yesterday:
            gaps = construct_gaps(
                start_date=latest_date,
                end_date=yesterday,
                chunk_size=settings.days_chunk_size
            )
            insert_gaps(gaps)
            logger.info(
                f"Inserted gaps for date range {latest_date} to {yesterday}"
            )


def check_metadata_exists(target_date: date) -> bool:
    """
    Check if metadata exists in DB for given date.
    
    Args:
        target_date: Date to check
        
    Returns:
        True if metadata exists
    """
    with db_session() as session:
        return session.execute(
            select(CRHoyMetadata)
            .where(CRHoyMetadata.date == target_date)
        ).first() is not None


def process_current_date() -> None:
    """Process metadata for current date."""
    current_date = get_costa_rica_today()
    logger.info(f"Processing metadata for current date {current_date}")
    
    # Update metadata for current date
    if not update_metadata_for_date(current_date):
        logger.error(f"Failed to update metadata for {current_date}")


def process_earliest_gap() -> None:
    """Process the earliest gap if exists."""
    gap = get_earliest_gap()
    if gap:
        logger.info(f"Processing earliest gap: {gap}")
        if process_gap(gap):
            logger.info(f"Successfully processed gap {gap}")
        else:
            logger.error(f"Failed to process gap {gap}")


def run_synchronizer() -> None:
    """
    Run the metadata synchronizer main loop.
    
    This function implements the main synchronizer flow:
    1. Handle initial gaps based on FIRST_DAY setting
    2. Enter main loop:
       - Check connectivity
       - If connected:
         - Check if metadata exists for current date
         - If not, handle day switch (gap identification)
         - Process current date
         - Process earliest gap if exists
       - Sleep until next check or exit is requested
    """
    logger.info("Starting CRHoy metadata synchronizer")
    
    # Handle initial gaps based on FIRST_DAY setting
    logger.info("Checking for initial gaps")
    handle_initial_gaps()
    
    # Main loop
    while not state.is_shutdown_requested():
        try:
            # Check connectivity
            if not check_connectivity():
                logger.warning("No connectivity, skipping this iteration")
                sleep_until_next_check(settings.check_updates_interval)
                continue
            
            # Get current date in Costa Rica timezone
            current_date = get_costa_rica_today()
            
            # Check if we need to handle day switch
            if not check_metadata_exists(current_date):
                logger.info(f"No metadata for {current_date}, handling day switch")
                handle_day_switch(current_date)
            
            # Process current date and earliest gap
            process_current_date()
            process_earliest_gap()
            
            # Sleep until next check or exit
            sleep_until_next_check(settings.check_updates_interval)
            
        except Exception as e:
            logger.error(f"Unexpected error in synchronizer: {e}")
            sleep_until_next_check(settings.check_updates_interval)
    
    logger.info("Metadata synchronizer shutdown complete")
