"""Scheduling functionality for CRHoy news downloader."""

from sqlalchemy import select

from ..common.api_client import check_internet_connection, check_website_availability
from ..common.logger import get_component_logger
from ..common.state import state
from ..common.utils import sleep_until_next_check
from ..settings import settings
from ..common.db import db_session
from ..common.models import CRHoySmartCategories
from .agent.prompts.category import initial_smart_categories
from .processor import process_news_chunk, NewsProcessorError
from bot.llm import initialize

logger = get_component_logger("downloader.scheduler")


def initialize_smart_categories() -> None:
    """
    Initialize the smart categories table if it's empty.
    
    This function checks if the crhoy_smart_categories table is empty and if so,
    populates it with the initial categories.
    """
    try:
        with db_session() as session:
            # Check if table is empty by selecting one record
            exists_flag = session.execute(select(CRHoySmartCategories).limit(1)).first() is not None
            
            if not exists_flag:
                logger.info("Initializing smart categories table")
                
                # Add all categories from initial_smart_categories
                for category, info in initial_smart_categories.items():
                    session.add(
                        CRHoySmartCategories(
                            category=category,
                            description=info["description"],
                            ignore=info["ignore"]
                        )
                    )
                
                session.commit()
                logger.info("Smart categories initialized successfully")
            else:
                logger.info("Smart categories table already initialized")
                
    except Exception as e:
        logger.error(f"Failed to initialize smart categories: {e}")
        raise


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


def run_downloader() -> None:
    """
    Run the news downloader main loop.
    
    This function implements the main downloader flow:
    1. Initialize LLM engine
    2. Initialize smart categories if needed
    3. Check connectivity
    4. If connected:
       - Process a chunk of news
    5. Sleep until next check or exit is requested
    """
    logger.info("Starting CRHoy news downloader")
    
    try:
        # Initialize LLM engine first
        logger.info("Initializing LLM engine")
        initialize()
        
        # Initialize smart categories
        initialize_smart_categories()
    except Exception as e:
        logger.error(f"Failed to initialize components, exiting: {e}")
        return
    
    while not state.is_shutdown_requested():
        try:
            # Check connectivity
            if not check_connectivity():
                logger.warning("No connectivity, skipping this iteration")
                sleep_until_next_check(settings.download_interval)
                continue
            
            # Process news chunk
            process_news_chunk()
            
            # Sleep until next check or exit
            sleep_until_next_check(settings.download_interval)
            
        except NewsProcessorError as e:
            logger.error(f"Error processing news: {e}")
            sleep_until_next_check(settings.download_interval)
            
        except Exception as e:
            logger.error(f"Unexpected error in downloader: {e}")
            sleep_until_next_check(settings.download_interval)
    
    logger.info("News downloader shutdown complete") 