"""Main entry point for CRHoy metadata synchronizer."""

import signal
import sys
from datetime import date
from typing import Optional

from ..common.db import init_db
from ..common.logger import get_component_logger, setup_logger
from ..settings import settings
from .gap_handler import get_earliest_gap, process_gap
from .scheduler import (
    check_connectivity,
    check_metadata_exists,
    get_costa_rica_today,
    handle_day_switch,
    handle_initial_gaps,
    sleep_until_next_check
)
from .updater import update_metadata_for_date

logger = get_component_logger("synchronizer.main")

# Global flag for graceful shutdown
should_exit = False


def signal_handler(signum: int, frame) -> None:
    """
    Handle termination signals.
    
    Args:
        signum: Signal number
        frame: Current stack frame
    """
    global should_exit
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    should_exit = True


def setup_signal_handlers() -> None:
    """Setup handlers for termination signals."""
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


def process_current_date(current_date: date) -> None:
    """
    Process metadata for current date.
    
    Args:
        current_date: Date to process
    """
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
    1. Initialize DB connection
    2. Handle initial gaps based on FIRST_DAY setting
    3. Enter main loop:
       - Get current date (Costa Rica timezone)
       - Check if metadata exists for current date
       - If not, handle day switch (gap identification)
       - Update metadata for current date
       - Process earliest gap if exists
       - Sleep until next check
    """
    logger.info("Starting CRHoy metadata synchronizer")
    
    try:
        # Initialize database
        logger.info("Initializing database connection")
        init_db(settings.database_url)
        
        # Handle initial gaps based on FIRST_DAY setting
        logger.info("Checking for initial gaps")
        handle_initial_gaps()
        
        # Main loop
        while not should_exit:
            # Get current date in Costa Rica timezone
            current_date = get_costa_rica_today()
            
            # Check connectivity
            if not check_connectivity():
                logger.warning("No connectivity, skipping this iteration")
                sleep_until_next_check()
                continue
            
            # Check if we need to handle day switch
            if not check_metadata_exists(current_date):
                logger.info(f"No metadata for {current_date}, handling day switch")
                handle_day_switch(current_date)
            
            # Process current date and earliest gap
            process_current_date(current_date)
            process_earliest_gap()
            
            if should_exit:
                break
                
            # Sleep until next check
            sleep_until_next_check()
            
    except Exception as e:
        logger.error(f"Unexpected error in synchronizer: {e}")
        sys.exit(1)
    finally:
        logger.info("Shutting down CRHoy metadata synchronizer")


def main() -> None:
    """Entry point for the synchronizer."""
    try:
        # Setup signal handlers for graceful shutdown
        setup_signal_handlers()
        
        # Run the synchronizer
        run_synchronizer()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
