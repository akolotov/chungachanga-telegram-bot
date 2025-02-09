"""Scheduling functionality for CRHoy news downloader."""

import time

from ..common.api_client import check_internet_connection, check_website_availability
from ..common.logger import get_component_logger
from ..common.state import state
from ..settings import settings
from .processor import process_news_chunk, NewsProcessorError

logger = get_component_logger("downloader.scheduler")


def check_connectivity(timeout: float = 5.0) -> bool:
    """
    Check if both internet and CRHoy website are available.
    
    Args:
        timeout: Timeout for connectivity checks in seconds
        
    Returns:
        True if both internet and website are available
    """
    if not check_internet_connection(timeout):
        logger.warning("No internet connection available")
        return False
        
    if not check_website_availability(timeout):
        logger.warning("CRHoy website is not available")
        return False
        
    return True


def sleep_until_next_check() -> None:
    """
    Sleep until next check interval or until exit is requested.
    Breaks early if shutdown is requested.
    """
    # Sleep in small intervals to check exit flag more frequently
    remaining = settings.download_interval
    while remaining > 0 and not state.is_shutdown_requested():
        sleep_time = min(1, remaining)  # Sleep max 1 second at a time
        time.sleep(sleep_time)
        remaining -= sleep_time


def run_downloader() -> None:
    """
    Run the news downloader main loop.
    
    This function implements the main downloader flow:
    1. Check connectivity
    2. If connected:
       - Process a chunk of news
    3. Sleep until next check or exit is requested
    """
    logger.info("Starting CRHoy news downloader")
    
    while not state.is_shutdown_requested():
        try:
            # Check connectivity
            if not check_connectivity():
                logger.warning("No connectivity, skipping this iteration")
                sleep_until_next_check()
                continue
            
            # Process news chunk
            process_news_chunk()
            
            # Sleep until next check or exit
            sleep_until_next_check()
            
        except NewsProcessorError as e:
            logger.error(f"Error processing news: {e}")
            sleep_until_next_check()
            
        except Exception as e:
            logger.error(f"Unexpected error in downloader: {e}")
            sleep_until_next_check()
    
    logger.info("News downloader shutdown complete") 