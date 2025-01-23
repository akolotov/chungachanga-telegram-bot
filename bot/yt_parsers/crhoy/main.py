import logging
from typing import List, Union

from bot.settings import settings

from .cache_db import CacheDB
from .helper import extract_video_id
from .models import CapturedNewsStory
from .yt_audio import extract_youtube_audio
from .transcript import transcribe_audio
from .reconstructor import get_stories_from_transctiption
from .audio_splitter import split_audio_for_stories

logger = logging.getLogger(__name__)

def transcribe_and_split(url: str, output_dir: str) -> Union[List[CapturedNewsStory], None]:
    """
    Process a CRHoy.com YouTube video by extracting audio, transcribing it,
    reconstructing news stories, and splitting the audio into segments.

    Args:
        url (str): URL of the YouTube video
        output_dir (str): Directory where to save the audio segments

    Returns:
        List[CapturedNewsStory]: List of captured news stories with their audio segments
    """
    # Extract video ID
    video_id = extract_video_id(url)
    if not video_id:
        return None

    # Initialize cache DB
    cache_db = CacheDB(settings.yt_crhoy_cache_db)

    logger.info(f"Extracting audio for video {video_id}")
    audio_path = extract_youtube_audio(url, cache_db)
    if not audio_path:
        return None
    logger.info(f"Audio for video extracted into {audio_path}")

    logger.info(f"Transcribing audio")
    transcription = transcribe_audio(video_id, cache_db)
    if not transcription:
        return None
    logger.info(f"Audio for video transcribed into '{transcription.text[:20]}...{transcription.text[-20:]}'")

    logger.info(f"Reconstructing news stories from transcription")
    stories = get_stories_from_transctiption(video_id, cache_db)
    if not stories:
        return None
    logger.info(f"Reconstructed {len(stories)} news stories")

    logger.info(f"Splitting audio on news stories")
    captured_stories = split_audio_for_stories(video_id, cache_db, output_dir)
    if not captured_stories:
        return None
    logger.info(f"Captured {len(captured_stories)} segments")

    return captured_stories 
