import logging
import os

from bot.settings import settings
from bot.llm import initialize

from ..cache_db import CacheDB
from ..helper import extract_video_id
from .main import get_stories_from_transctiption

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

yt_link = os.getenv("YT_LINK", "")
if not yt_link:
    print("YT_LINK environment variable is not set. Please set it in your environment or in a .env file.")
    exit(1)

# Extract video ID
video_id = extract_video_id(yt_link)
if not video_id:
    print(f"Invalid YouTube URL: {yt_link}")
    exit(1)

# Initialize LLM
initialize()

# Initialize cache DB
cache_db = CacheDB(settings.yt_crhoy_cache_db)

# Check if transcription exists
if not cache_db.get_transcription(video_id):
    print(f"No transcription found for video {video_id}")
    exit(1)

# Forces ignore cache and reprocess for testing. It is OK to run this multiple times
# since free tier of Gemini is used.
stories = get_stories_from_transctiption(video_id, cache_db, force=True)
if stories:
    print("Processing successful!")
    print("Final Stories:")
    for story in stories:
        print(f"- {story}")
else:
    print("Failed to process transcription") 