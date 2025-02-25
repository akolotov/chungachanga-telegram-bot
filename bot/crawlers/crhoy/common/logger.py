"""Logging configuration for CRHoy crawler components."""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class TimeZoneFormatter(logging.Formatter):
    """Custom formatter that supports configurable timezone for timestamps."""
    
    def __init__(self, fmt: str, use_utc: bool = True):
        """
        Initialize formatter with timezone configuration.
        
        Args:
            fmt: Format string for the log message
            use_utc: If True, use UTC time; if False, use local time
        """
        super().__init__(fmt)
        self.use_utc = use_utc
    
    def formatTime(self, record: logging.LogRecord, datefmt: Optional[str] = None) -> str:
        """
        Format the time according to the configured timezone.
        
        Args:
            record: Log record to format
            datefmt: Optional datetime format string
            
        Returns:
            Formatted timestamp string
        """
        if self.use_utc:
            # Use fromtimestamp with explicit UTC timezone instead of deprecated utcfromtimestamp
            dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        else:
            # For local time, use fromtimestamp without timezone
            dt = datetime.fromtimestamp(record.created)
            
        if datefmt:
            return dt.strftime(datefmt)
            
        return dt.isoformat(sep=' ', timespec='seconds')


def setup_logger(
    component_name: str,
    log_level: int = logging.INFO,
    log_file: Optional[Path] = None,
    use_utc: bool = True,
) -> logging.Logger:
    """
    Configure and return a logger for a crawler component.

    Args:
        component_name: Name of the component (e.g., 'synchronizer' or 'downloader')
        log_level: Logging level (default: INFO)
        log_file: Optional path to log file. If not provided, logs to stderr only
        use_utc: If True, use UTC time in logs; if False, use local time

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(f"crhoy_crawler.{component_name}")
    logger.setLevel(log_level)

    # Create formatters with configured timezone
    detailed_formatter = TimeZoneFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        use_utc=use_utc
    )
    simple_formatter = TimeZoneFormatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        use_utc=use_utc
    )

    # Console handler (detailed format)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(detailed_formatter)
    logger.addHandler(console_handler)

    # File handler if log_file is provided (detailed format)
    if log_file:
        # Ensure log directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)

    return logger


def get_component_logger(
    component_name: str,
    use_utc: bool = False
) -> logging.Logger:
    """
    Get an existing logger for a component or create a new one with default settings.

    Args:
        component_name: Name of the component (e.g., 'synchronizer' or 'downloader')
        use_utc: If True, use UTC time in logs; if False, use local time

    Returns:
        Logger instance for the component
    """
    logger = logging.getLogger(f"crhoy_crawler.{component_name}")
    if not logger.handlers:  # Only setup if no handlers exist
        logger = setup_logger(component_name, use_utc=use_utc)
    return logger
