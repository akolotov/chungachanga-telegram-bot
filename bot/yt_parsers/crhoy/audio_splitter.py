import logging
import os
from typing import List, Union

from pydub import AudioSegment

from .cache_db import CacheDB
from .models import CapturedNewsStory
from .time_marks import find_story_timestamps

logger = logging.getLogger(__name__)

YOUTUBE_URL_BASE = "https://youtu.be/"

def split_audio_for_stories(video_id: str, cache_db: CacheDB, output_dir: str) -> Union[List[CapturedNewsStory], None]:
    """
    Split audio file into segments based on news story timestamps.
    
    Args:
        video_id (str): YouTube video ID
        cache_db (CacheDB): Cache database instance
        output_dir (str): Directory to save audio segments
        
    Returns:
        List[CapturedNewsStory]: List of news stories with their audio file paths
    """

    logger.info(f"Splitting audio for video {video_id} into segments")

    # Get audio file path from cache
    audio_path = cache_db.get_audio_path(video_id)
    if not audio_path:
        logger.error(f"No audio file found for video")
        return None
    
    # Find story timestamps
    stories = find_story_timestamps(video_id, cache_db)
    if not stories:
        logger.error(f"No story time marks found")
        return None
    logger.info(f"Will use time marks for {len(stories)} stories")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Load the audio file
    try:
        audio = AudioSegment.from_mp3(audio_path)
    except Exception as e:
        logger.error(f"Failed to load audio file {audio_path}: {str(e)}")
        return None

    captured_stories = []

    # Process each story that has valid timestamps
    for story in stories:
        logger.info(f"Cutting audio for story '{story.text[:20]}...{story.text[-20:]}'")
        if story.start is None or story.end is None:
            logger.warning(f"Skipping story due to missing time marks")
            continue

        try:
            # Convert seconds to milliseconds
            start_ms = int(story.start * 1000)
            end_ms = int(story.end * 1000)

            # Extract segment
            segment_audio = audio[start_ms:end_ms]

            # Create output filename
            output_file = os.path.join(output_dir, f"story_{story.id}.mp3")

            # Export segment
            segment_audio.export(output_file, format="mp3")

            # Create YouTube URL with timestamp
            youtube_url = f"{YOUTUBE_URL_BASE}{video_id}?t={int(story.start)}"

            # Create CapturedNewsStory
            captured_story = CapturedNewsStory(
                id=story.id,
                text=story.text,
                audio=output_file,
                url=youtube_url
            )
            captured_stories.append(captured_story)

        except Exception as e:
            logger.error(f"Failed to process story: {str(e)}")
            continue

    return captured_stories


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    from bot.settings import settings
    from .helper import ensure_video_cache_dir, extract_video_id

    yt_link = os.getenv("YT_LINK", "")
    if not yt_link:
        print("YT_LINK environment variable is not set. Please set it in your environment or in a .env file.")
        exit(1)

    # Extract video ID
    video_id = extract_video_id(yt_link)
    if not video_id:
        print(f"Invalid YouTube URL: {yt_link}")
        exit(1)

    # Initialize cache DB
    cache_db = CacheDB(settings.yt_crhoy_cache_db)

    # Get output directory
    output_dir = ensure_video_cache_dir(video_id)
    
    # Split audio and get captured stories
    captured_stories = split_audio_for_stories(video_id, cache_db, output_dir)
    
    if captured_stories:
        print(f"\nSuccessfully processed {len(captured_stories)} stories:")
        for story in captured_stories:
            print(f"\nStory ID: {story.id}")
            print(f"Text: {story.text[:16]}...")
            print(f"Audio file: {story.audio}")
            print(f"YouTube URL: {story.url}")
    else:
        print("No stories were processed successfully.")
