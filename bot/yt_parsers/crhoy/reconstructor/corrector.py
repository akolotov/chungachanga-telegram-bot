import json
import logging
from typing import Dict, List, Union

from bot.llm import (
    BaseStructuredOutput,
    ChatModelConfig,
    DeserializationError,
    GeminiChatModel,
    UnexpectedFinishReason,
)
from bot.llm.gemini import response_content as content
from bot.settings import settings
from bot.types import LLMEngine

from ..cache_db import CacheDB
from .prompts import corrector_prompt, corrector_prompt_so

logger = logging.getLogger(__name__)


class CorrectedStories(BaseStructuredOutput):
    stories: List[Dict[str, Union[str, bool]]]

    @classmethod
    def llm_schema(cls, _engine: LLMEngine) -> content.Schema:
        return corrector_prompt_so

    @classmethod
    def deserialize(cls, json_str: str, _engine: LLMEngine) -> "CorrectedStories":
        try:
            corrected = json.loads(json_str)

            return CorrectedStories(
                stories=corrected["stories"]
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise DeserializationError(f"Failed to parse Gemini response: {e}")
        except ValueError as e:
            logger.error(f"Invalid data in Gemini response: {e}")
            raise DeserializationError(f"Invalid data in Gemini response: {e}")


class Corrector(GeminiChatModel):
    """A specialized chat model for correcting transcribed news stories.

    This class extends GeminiChatModel to correct spelling and punctuation in transcribed text.
    It processes news stories to ensure proper spelling of names, places, and organizations,
    and adds necessary punctuation.

    Inherits from:
        GeminiChatModel: Base class for Gemini model interactions
    """

    def __init__(self, model_name: str, session_id: str = ""):
        """Initialize the Corrector with specific configuration.

        Args:
            model_name (str): Name of the Gemini model to use
            session_id (str): Unique identifier to track agents' responses belong to the same session
        """

        model_config = ChatModelConfig(
            session_id=session_id,
            agent_id="corrector",
            llm_model_name=model_name,
            temperature=0.2,
            system_prompt=corrector_prompt,
            response_class=CorrectedStories,
            max_tokens=8192,
            keep_raw_engine_responses=settings.keep_raw_engine_responses,
            raw_engine_responses_dir=settings.raw_engine_responses_dir
        )
        super().__init__(model_config)

    def adjust(self, video_id: str, cache_db: CacheDB, force: bool = False) -> Union[List[str], None]:
        """Correct spelling and punctuation in transcribed news stories.

        Takes video ID to get stories from cache and corrects any spelling or punctuation issues.
        Uses cache to avoid unnecessary LLM calls.

        Args:
            video_id (str): YouTube video ID
            cache_db (CacheDB): Cache database instance
            force (bool): If True, force new correction even if cached version exists

        Returns:
            List[str] or None: List of corrected stories if successful, None if error
        """

        # Check cache first
        if not force:
            cached_stories = cache_db.get_final_local_news(video_id)
            if cached_stories:
                logger.info(f"Found cached final stories for video {video_id}")
                return cached_stories

        logger.info(f"Proofreading news stories")

        # Get stories from cache
        raw_stories = cache_db.get_raw_local_news(video_id)
        if not raw_stories:
            logger.error(f"No raw local stories found for video {video_id}")
            return None

        try:
            model_response = self.generate_response(json.dumps(raw_stories))
        except UnexpectedFinishReason as e:
            logger.error(f"LLM engine responded with: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            return None

        # Get corrected stories
        corrected_stories = [
            story["text"] for story in model_response.response.stories
        ]

        # Cache the result
        cache_db.set_final_local_news(video_id, corrected_stories)

        return corrected_stories


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    # Example usage
    from bot.llm import initialize
    import os
    from ..helper import extract_video_id

    yt_link = os.getenv("YT_LINK", "")
    if not yt_link:
        print("YT_LINK environment variable is not set. Please set it in your environment or in a .env file.")
        exit(1)

    # Extract video ID
    video_id = extract_video_id(yt_link)
    if not video_id:
        print(f"Invalid YouTube URL: {yt_link}")
        exit(1)

    initialize()

    corrector = Corrector(settings.agent_engine_model)
    cache_db = CacheDB(settings.yt_crhoy_cache_db)

    corrected_stories = corrector.adjust(video_id, cache_db)
    if corrected_stories:
        print("Correction successful!")
        print("Corrected Stories:")
        for story in corrected_stories:
            print(f"- {story}")
    else:
        print("Failed to correct news stories")
