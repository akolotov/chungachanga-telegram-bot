import logging
import os

import yt_dlp

from bot.settings import settings

from .cache_db import CacheDB
from .helper import extract_video_id, ensure_video_cache_dir

logger = logging.getLogger(__name__)

def extract_youtube_audio(url: str, cache_db: CacheDB) -> str:
    """
    Extract audio from a YouTube video, using cache when available.
    
    Args:
        url (str): YouTube video URL
        cache_db (CacheDB): Cache database instance
        
    Returns:
        str: Path to the audio file if successful, empty string otherwise
    """
    # Extract video ID from URL
    video_id = extract_video_id(url)
    if not video_id:
        logger.error(f"Invalid YouTube URL: {url}")
        return ""

    # Check if audio exists in cache
    if cache_db.video_exists(video_id):
        audio_path = cache_db.get_audio_path(video_id)
        if audio_path and os.path.exists(audio_path):
            logger.info(f"Found cached audio for video {video_id}")
            return audio_path

    # Get video cache directory
    video_cache_dir = ensure_video_cache_dir(video_id)

    # Construct output path
    output_path = os.path.join(video_cache_dir, "audio.mp3")

    # Remove .mp3 extension for yt-dlp (it will be added by the postprocessor)
    output_template = output_path[:-4]

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'logger': logger,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'noplaylist': True,
    }

    logger.info(f"Getting audio from YT video {url}")
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Update cache with new audio path
        cache_db.set_audio_path(video_id, output_path)
        
        return output_path
    except Exception as e:
        logger.error(f"Error extracting audio: {e}")
        return ""

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    yt_link = os.getenv("YT_LINK", "")

    if len(yt_link) > 0:
        cache_db = CacheDB(settings.yt_crhoy_cache_db)
        audio_path = extract_youtube_audio(yt_link, cache_db)
        if audio_path:
            print(f"Audio track of {yt_link} saved at: {audio_path}")
        else:
            print(f"Failed to extract audio track from {yt_link}.")
    else:
        print("YT_LINK environment variable is not set. Please set it in your environment or in a .env file.")