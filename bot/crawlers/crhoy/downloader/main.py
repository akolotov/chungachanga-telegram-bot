"""Main entry point for CRHoy news downloader."""

import signal
import sys

from ..common.db import init_db
from ..common.logger import get_component_logger
from ..common.state import state
from ..settings import settings
from .scheduler import run_downloader

logger = get_component_logger("downloader.main")


def signal_handler(signum: int, frame) -> None:
    """
    Handle termination signals.
    
    Args:
        signum: Signal number
        frame: Current stack frame
    """
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    state.request_shutdown()


def setup_signal_handlers() -> None:
    """Setup handlers for termination signals."""
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


def main() -> None:
    """Entry point for the downloader."""
    try:
        # Setup signal handlers for graceful shutdown
        setup_signal_handlers()
        
        # Initialize database connection
        logger.info("Initializing database connection")
        init_db(settings.database_url)
        
        # Run the downloader
        run_downloader()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 