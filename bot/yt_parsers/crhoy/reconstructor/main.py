import logging
from typing import List, Union

from bot.settings import settings

from ..cache_db import CacheDB
from .extractor import Extractor
from .localizer import Localizer
from .corrector import Corrector

logger = logging.getLogger(__name__)


def get_stories_from_transctiption(video_id: str, cache_db: CacheDB, force: bool = False) -> Union[List[str], None]:
    """Process transcription text through the pipeline to get Costa Rica related news stories.

    The pipeline consists of three steps:
    1. Extract individual news stories from transcription
    2. Filter stories to keep only those related to Costa Rica
    3. Correct spelling and punctuation in the filtered stories

    Args:
        video_id (str): YouTube video ID
        cache_db (CacheDB): Cache database instance
        force (bool): If True, force new processing even if cached version exists

    Returns:
        List[str] or None: List of processed news stories if successful, None if error
    """

    # Check cache first
    if not force:
        cached_stories = cache_db.get_final_local_news(video_id)
        if cached_stories:
            logger.info(f"Found cached final stories for video {video_id}")
            return cached_stories

    logger.info(f"Processing transcription for video {video_id}")

    # Initialize components
    extractor = Extractor(settings.agent_engine_model)
    localizer = Localizer(settings.agent_engine_model)
    corrector = Corrector(settings.agent_engine_model)

    # Step 1: Extract stories
    logger.info("Extracting stories from transcription")
    stories = extractor.split(video_id, cache_db, force)
    if not stories:
        logger.error("Failed to extract stories from transcription")
        return None
    logger.info(f"Extracted {len(stories)} stories")

    # Step 2: Filter local stories
    logger.info("Filtering local stories")
    local_stories = localizer.filter(video_id, cache_db, force)
    if not local_stories:
        logger.error("Failed to filter local stories")
        return None
    logger.info(f"Left with {len(local_stories)} stories")

    # Step 3: Correct stories
    logger.info("Correcting stories")
    corrected_stories = corrector.adjust(video_id, cache_db, force)
    if not corrected_stories:
        logger.error("Failed to correct stories")
        return None
    logger.info(f"Finalized {len(corrected_stories)} stories")

    return corrected_stories 