"""File system operations for CRHoy crawler."""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .logger import get_component_logger

logger = get_component_logger("file_manager")


class FileManagerError(Exception):
    """Base exception for file manager errors."""
    pass


def get_metadata_path(base_dir: Path, target_date: date) -> Path:
    """
    Get the path for metadata JSON file.

    Args:
        base_dir: Base directory for all crawler data
        target_date: Date for which to get metadata path

    Returns:
        Path object for the metadata file
    """
    return base_dir / "metadata" / str(target_date.year) / f"{target_date.strftime('%m')}" / f"{target_date.strftime('%d')}.json"


def get_news_path(base_dir: Path, timestamp: datetime, news_id: int) -> Path:
    """
    Get the path for news content file.

    Args:
        base_dir: Base directory for all crawler data
        timestamp: Timestamp of the news
        news_id: ID of the news article

    Returns:
        Path object for the news content file
    """
    return (
        base_dir / "news" / 
        timestamp.strftime("%Y-%m-%d") / 
        f"{timestamp.strftime('%H-%M')}-{news_id}.md"
    )


def ensure_dir(path: Path) -> None:
    """
    Ensure directory exists, create if it doesn't.

    Args:
        path: Directory path to ensure

    Raises:
        FileManagerError: If directory creation fails
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise FileManagerError(f"Failed to create directory {path}: {e}")


def save_metadata(
    base_dir: Path,
    target_date: date,
    metadata: Dict[str, Any]
) -> Path:
    """
    Save metadata to JSON file.

    Args:
        base_dir: Base directory for all crawler data
        target_date: Date of the metadata
        metadata: Metadata dictionary to save

    Returns:
        Path where metadata was saved

    Raises:
        FileManagerError: If saving fails
    """
    file_path = get_metadata_path(base_dir, target_date)
    
    try:
        # Ensure directory exists
        ensure_dir(file_path.parent)
        
        # Save metadata with pretty formatting
        with file_path.open('w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Saved metadata to {file_path}")
        return file_path
        
    except Exception as e:
        raise FileManagerError(f"Failed to save metadata to {file_path}: {e}")


def load_metadata(
    base_dir: Path,
    target_date: date
) -> Optional[Dict[str, Any]]:
    """
    Load metadata from JSON file.

    Args:
        base_dir: Base directory for all crawler data
        target_date: Date of the metadata to load

    Returns:
        Metadata dictionary if file exists, None otherwise

    Raises:
        FileManagerError: If loading fails
    """
    file_path = get_metadata_path(base_dir, target_date)
    
    if not file_path.exists():
        logger.debug(f"No metadata file found at {file_path}")
        return None
        
    try:
        with file_path.open('r', encoding='utf-8') as f:
            metadata = json.load(f)
            
        logger.debug(f"Loaded metadata from {file_path}")
        return metadata
        
    except Exception as e:
        raise FileManagerError(f"Failed to load metadata from {file_path}: {e}")


def save_news_content(
    base_dir: Path,
    timestamp: datetime,
    news_id: int,
    title: str,
    content: str
) -> Path:
    """
    Save news content to markdown file.

    Args:
        base_dir: Base directory for all crawler data
        timestamp: Timestamp of the news
        news_id: ID of the news article
        title: Title of the news article
        content: Markdown content of the news article

    Returns:
        Path where content was saved

    Raises:
        FileManagerError: If saving fails
    """
    file_path = get_news_path(base_dir, timestamp, news_id)
    
    try:
        # Ensure directory exists
        ensure_dir(file_path.parent)
        
        # Save content with title as h1 header
        with file_path.open('w', encoding='utf-8') as f:
            f.write(f"# {title}\n\n")
            f.write(content)
            
        logger.info(f"Saved news content to {file_path}")
        return file_path
        
    except Exception as e:
        raise FileManagerError(f"Failed to save news content to {file_path}: {e}")


def load_news_content(
    base_dir: Path,
    timestamp: datetime,
    news_id: int
) -> Optional[str]:
    """
    Load news content from markdown file.

    Args:
        base_dir: Base directory for all crawler data
        timestamp: Timestamp of the news
        news_id: ID of the news article

    Returns:
        News content if file exists, None otherwise

    Raises:
        FileManagerError: If loading fails
    """
    file_path = get_news_path(base_dir, timestamp, news_id)
    
    if not file_path.exists():
        logger.debug(f"No news content file found at {file_path}")
        return None
        
    try:
        with file_path.open('r', encoding='utf-8') as f:
            content = f.read()
            
        logger.debug(f"Loaded news content from {file_path}")
        return content
        
    except Exception as e:
        raise FileManagerError(f"Failed to load news content from {file_path}: {e}")
