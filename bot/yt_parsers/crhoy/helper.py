import logging
import re
import os

from bot.settings import settings

logger = logging.getLogger(__name__)

def extract_video_id(url: str) -> str:
    """
    Extract the video ID from a YouTube URL.
    
    Args:
        url (str): YouTube video URL in various possible formats:
            - https://www.youtube.com/watch?v=VIDEO_ID
            - https://youtu.be/VIDEO_ID
            - https://youtu.be/VIDEO_ID?list=PLAYLIST_ID
            
    Returns:
        str: YouTube video ID if found, empty string otherwise
    """
    # Patterns to match different YouTube URL formats
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com/v/)([a-zA-Z0-9_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
            
    logger.warning(f"Could not extract video ID from URL: {url}")
    return ""

def ensure_video_cache_dir(video_id: str) -> str:
    """
    Ensure the video-specific cache directory exists and return its path.
    
    Args:
        video_id (str): YouTube video ID
        
    Returns:
        str: Path to the video cache directory
    """
    video_cache_dir = os.path.join(settings.yt_crhoy_cache_dir, video_id)
    os.makedirs(video_cache_dir, exist_ok=True)
    return video_cache_dir
