import json
import logging
from typing import List, Union

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
from ..models import TranscribedSequences
from .prompts import extractor_prompt, extractor_prompt_so

logger = logging.getLogger(__name__)


class ExtractedSequences(BaseStructuredOutput):
    intro: str
    stories: list[str]
    outro: str

    @classmethod
    def llm_schema(cls, _engine: LLMEngine) -> content.Schema:
        return extractor_prompt_so

    @classmethod
    def deserialize(cls, json_str: str, _engine: LLMEngine) -> "ExtractedSequences":
        try:
            sequences = json.loads(json_str)

            return ExtractedSequences(
                intro=sequences["intro"],
                stories=sequences["stories"],
                outro=sequences["outro"]
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise DeserializationError(f"Failed to parse Gemini response: {e}")


class Extractor(GeminiChatModel):
    """A specialized chat model for extracting news stories from transcribed text.

    This class extends GeminiChatModel to split transcribed text into separate news stories.
    It processes transcribed text to identify intro, individual news stories, and outro.

    Inherits from:
        GeminiChatModel: Base class for Gemini model interactions
    """

    def __init__(self, model_name: str, session_id: str = ""):
        """Initialize the Extractor with specific configuration.

        Args:
            model_name (str): Name of the Gemini model to use
            session_id (str): Unique identifier to track agents' responses belong to the same session
        """

        model_config = ChatModelConfig(
            session_id=session_id,
            agent_id="extractor",
            llm_model_name=model_name,
            temperature=1.0,
            system_prompt=extractor_prompt,
            response_class=ExtractedSequences,
            max_tokens=8192,
            keep_raw_engine_responses=settings.keep_raw_engine_responses,
            raw_engine_responses_dir=settings.raw_engine_responses_dir
        )
        super().__init__(model_config)

    def split(self, video_id: str, cache_db: CacheDB, force: bool = False) -> Union[List[str], None]:
        """Split transcribed text into separate news stories.

        Takes video ID to get transcribed text from cache and extracts individual news stories.
        Uses cache to avoid unnecessary LLM calls.

        Args:
            video_id (str): YouTube video ID
            cache_db (CacheDB): Cache database instance
            force (bool): If True, force new extraction even if cached version exists

        Returns:
            List[str] or None: List of extracted news stories if successful, None if error
        """

        # Check cache first
        if not force:
            cached_sequences = cache_db.get_sequences(video_id)
            if cached_sequences:
                logger.info(f"Found cached sequences for video {video_id}")
                return cached_sequences.stories

        logger.info(f"Splitting transcription into logically separated segments")

        # Get transcription from cache
        transcription_data = cache_db.get_transcription(video_id)
        if not transcription_data:
            logger.error(f"Transcription not found for video {video_id}")
            return None

        try:
            model_response = self.generate_response(transcription_data.text)
        except UnexpectedFinishReason as e:
            logger.error(f"LLM engine responded with: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            return None

        # Convert ExtractedSequences to TranscribedSequences for caching
        sequences = TranscribedSequences(
            intro=model_response.response.intro,
            stories=model_response.response.stories,
            outro=model_response.response.outro
        )

        # Cache the result
        cache_db.set_sequences(video_id, sequences)

        return sequences.stories


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

    extractor = Extractor(settings.agent_engine_model)
    cache_db = CacheDB(settings.yt_crhoy_cache_db)

    stories = extractor.split(video_id, cache_db)
    if stories:
        print("Extraction successful!")
        print("Stories:")
        for story in stories:
            print(f"- {story}")
    else:
        print("Failed to extract stories")
