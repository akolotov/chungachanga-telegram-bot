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
from .prompts import localizator_prompt, localizator_prompt_so

logger = logging.getLogger(__name__)


class LocalizedStories(BaseStructuredOutput):
    stories: List[Dict[str, Union[str, bool]]]

    @classmethod
    def llm_schema(cls, _engine: LLMEngine) -> content.Schema:
        return localizator_prompt_so

    @classmethod
    def deserialize(cls, json_str: str, _engine: LLMEngine) -> "LocalizedStories":
        try:
            localized = json.loads(json_str)

            return LocalizedStories(
                stories=localized["stories"]
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise DeserializationError(f"Failed to parse Gemini response: {e}")
        except ValueError as e:
            logger.error(f"Invalid data in Gemini response: {e}")
            raise DeserializationError(f"Invalid data in Gemini response: {e}")


class Localizer(GeminiChatModel):
    """A specialized chat model for filtering Costa Rica related news stories.

    This class extends GeminiChatModel to identify which news stories are related to Costa Rica.
    It processes a list of news stories and identifies which ones are about Costa Rica.

    Inherits from:
        GeminiChatModel: Base class for Gemini model interactions
    """

    def __init__(self, model_name: str, session_id: str = ""):
        """Initialize the Localizer with specific configuration.

        Args:
            model_name (str): Name of the Gemini model to use
            session_id (str): Unique identifier to track agents' responses belong to the same session
        """

        model_config = ChatModelConfig(
            session_id=session_id,
            agent_id="localizer",
            llm_model_name=model_name,
            temperature=0.2,
            system_prompt=localizator_prompt,
            response_class=LocalizedStories,
            max_tokens=8192,
            keep_raw_engine_responses=settings.keep_raw_engine_responses,
            raw_engine_responses_dir=settings.raw_engine_responses_dir
        )
        super().__init__(model_config)

    def filter(self, video_id: str, cache_db: CacheDB, force: bool = False) -> Union[List[str], None]:
        """Filter news stories to identify those related to Costa Rica.

        Takes video ID to get stories from cache and identifies which ones are related to Costa Rica.
        Uses cache to avoid unnecessary LLM calls.

        Args:
            video_id (str): YouTube video ID
            cache_db (CacheDB): Cache database instance
            force (bool): If True, force new filtering even if cached version exists

        Returns:
            List[str] or None: List of stories related to Costa Rica if successful, None if error
        """

        # Check cache first
        if not force:
            cached_stories = cache_db.get_raw_local_news(video_id)
            if cached_stories:
                logger.info(f"Found cached local stories for video {video_id}")
                return cached_stories

        logger.info(f"Filtering local news stories")

        # Get stories from cache
        sequences = cache_db.get_sequences(video_id)
        if not sequences:
            logger.error(f"No stories found for video {video_id}")
            return None

        # Prepare stories with IDs for the model
        stories_with_ids = [
            {
                "id": f"{i+1:03d}",
                "text": story
            } for i, story in enumerate(sequences.stories)
        ]

        try:
            model_response = self.generate_response(json.dumps(stories_with_ids))
        except UnexpectedFinishReason as e:
            logger.error(f"LLM engine responded with: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            return None

        # Get stories related to Costa Rica
        local_stories = [
            story["text"] for story in stories_with_ids
            if any(
                response_story["id"] == story["id"] and response_story["is_related_to_costa_rica"]
                for response_story in model_response.response.stories
            )
        ]

        # Cache the result
        cache_db.set_raw_local_news(video_id, local_stories)

        return local_stories


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

    localizer = Localizer(settings.agent_engine_model)
    cache_db = CacheDB(settings.yt_crhoy_cache_db)

    local_stories = localizer.filter(video_id, cache_db)
    if local_stories:
        print("Filtering successful!")
        print("Local Stories:")
        for story in local_stories:
            print(f"- {story}") 
    else:
        print("Failed to filter local news stories")
