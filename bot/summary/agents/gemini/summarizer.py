# Python standard library imports
import json
import logging
from typing import Literal, Union

# Local imports
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

from ...models import ResponseError
from .exceptions import GeminiSummarizerError
from .prompts import news_article_example, system_prompt_summarizer as system_prompt

logger = logging.getLogger(__name__)


class MinimalNewsSummary(BaseStructuredOutput):
    voice_tag: Literal['male', 'female']
    news_original: str

    @classmethod
    def llm_schema(cls, _engine: LLMEngine) -> content.Schema:
        return content.Schema(
            type=content.Type.OBJECT,
            enum=[],
            required=["a_news_analysis", "b_voice_tag", "c_composed_news"],
            properties={
                "a_news_analysis": content.Schema(
                    type=content.Type.OBJECT,
                    enum=[],
                    required=["a_mainActor", "b_otherActors", "c_mainAction", "d_additionalActions", "e_timeOrientation",
                            "f_location", "g_target", "h_reason", "i_consequences", "j_contextBackground", "k_keyPoints", "l_sentiment"],
                    properties={
                        "a_mainActor": content.Schema(
                            type=content.Type.STRING,
                        ),
                        "b_otherActors": content.Schema(
                            type=content.Type.ARRAY,
                            items=content.Schema(
                                type=content.Type.STRING,
                            ),
                        ),
                        "c_mainAction": content.Schema(
                            type=content.Type.STRING,
                        ),
                        "d_additionalActions": content.Schema(
                            type=content.Type.ARRAY,
                            items=content.Schema(
                                type=content.Type.STRING,
                            ),
                        ),
                        "e_timeOrientation": content.Schema(
                            type=content.Type.STRING,
                        ),
                        "f_location": content.Schema(
                            type=content.Type.STRING,
                        ),
                        "g_target": content.Schema(
                            type=content.Type.STRING,
                        ),
                        "h_reason": content.Schema(
                            type=content.Type.STRING,
                        ),
                        "i_consequences": content.Schema(
                            type=content.Type.ARRAY,
                            items=content.Schema(
                                type=content.Type.OBJECT,
                                enum=[],
                                required=["a_type", "b_description"],
                                properties={
                                    "a_type": content.Schema(
                                        type=content.Type.STRING,
                                    ),
                                    "b_description": content.Schema(
                                        type=content.Type.STRING,
                                    ),
                                },
                            ),
                        ),
                        "j_contextBackground": content.Schema(
                            type=content.Type.STRING,
                        ),
                        "k_keyPoints": content.Schema(
                            type=content.Type.ARRAY,
                            items=content.Schema(
                                type=content.Type.STRING,
                            ),
                        ),
                        "l_sentiment": content.Schema(
                            type=content.Type.STRING,
                        ),
                    },
                ),
                "b_voice_tag": content.Schema(
                    type=content.Type.STRING,
                ),
                "c_composed_news": content.Schema(
                    type=content.Type.STRING,
                ),
            },
        )

    @classmethod
    def deserialize(cls, json_str: str, _engine: LLMEngine) -> "MinimalNewsSummary":
        try:
            summary_output = json.loads(json_str)

            return MinimalNewsSummary(
                voice_tag=summary_output["b_voice_tag"],
                news_original=summary_output["c_composed_news"]
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise DeserializationError(
                f"Failed to parse Gemini response: {e}")

class Summarizer(GeminiChatModel):
    """A specialized chat model for summarizing news articles in Spanish.

    This class extends BaseChatModel to create concise, easy-to-understand news announcements
    targeted at non-native Spanish speakers. It processes news articles to create ~20-second
    summaries suitable for radio broadcasting, assigns appropriate voice tags, and ensures
    B1-level Spanish language complexity.

    The summarizer follows specific guidelines for content creation:
    - Uses B1 level Spanish (CEFR scale)
    - Limits summaries to 3 sentences
    - Avoids complex terminology and idioms
    - Maintains cultural sensitivity
    - Assigns male/female voice tags based on news category

    Inherits from:
        BaseChatModel: Base class for Gemini model interactions
    """

    def __init__(self, model_name: str, session_id: str = ""):
        """Initialize the Summarizer with specific configuration for news summarization.

        Args:
            model_name (str): Name of the Gemini model to use
            session_id (str): Unique identifier to track agents' responses belong to the same session
        """

        logger.info(f"Using Gemini model {model_name}.")

        model_config = ChatModelConfig(
            session_id=session_id,
            agent_id="summarizer",
            llm_model_name=model_name,
            temperature=1.0,
            system_prompt=system_prompt,
            response_class=MinimalNewsSummary,
            max_tokens=8192,
            keep_raw_engine_responses=settings.keep_raw_engine_responses,
            raw_engine_responses_dir=settings.raw_engine_responses_dir
        )
        super().__init__(model_config)

    def generate(self, news_article: str) -> Union[MinimalNewsSummary, ResponseError]:
        """Process a news article to create a concise, radio-friendly summary.

        Takes a Spanish news article as input and generates a simplified summary suitable
        for radio broadcasting, including an appropriate voice tag for the announcer.

        Args:
            news_article (str): The original Spanish news article text to be summarized.

        Returns:
            MinimalNewsSummary or ResponseError:
                - MinimalNewsSummary: Object containing:
                    - voice_tag: Gender tag for the announcer (male/female)
                    - news_original: Simplified B1-level Spanish summary
                - ResponseError: Error details if the summarization fails
        """

        logger.info(f"Sending a request to Gemini to create a news summary.")

        try:
            model_response = self.generate_response(news_article)
        except UnexpectedFinishReason as e:
            return ResponseError(error=f"LLM engine responded with: {e}")
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            raise GeminiSummarizerError(f"Failed to generate response: {e}")
        
        return model_response.response

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    from bot.llm import initialize

    api_key = settings.agent_engine_api_key
    if not api_key:
        raise GeminiSummarizerError(
            "Gemini API key not found. Please set the AGENT_ENGINE_API_KEY environment variable.")

    initialize()

    summarizer = Summarizer(settings.agent_engine_model)
    summary = summarizer.generate(news_article_example)

    if isinstance(summary, ResponseError):
        print(f"Error: {summary.error}")
    else:
        print("Summary Created Successfully!")
        print(f"Voice Tag: {summary.voice_tag}")
        print(f"Spanish Summary: {summary.news_original}")
