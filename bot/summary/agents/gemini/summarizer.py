import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content
import logging
import json
from typing import Union

from ...models import MinimalNewsSummary, ResponseError
from .prompts import system_prompt_summarizer as system_prompt
from .prompts import news_article_example
from .base import BaseChatModel, ChatModelConfig
from .exceptions import GeminiSummarizerError, GeminiUnexpectedFinishReason
from bot.settings import settings

logger = logging.getLogger(__name__)

news_summary_schema = content.Schema(
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


class Summarizer(BaseChatModel):
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
            response_schema=news_summary_schema,
            max_tokens=8192
        )
        super().__init__(model_config)

    def generate(self, news_article: str) -> Union[MinimalNewsSummary, ResponseError]:
        """Process a news article to create a concise, radio-friendly summary.

        Takes a Spanish news article as input and generates a simplified summary suitable
        for radio broadcasting, including an appropriate voice tag for the announcer.

        Args:
            news_article (str): The original Spanish news article text to be summarized.

        Returns:
            - MinimalNewsSummary: Object containing:
                - voice_tag: Gender tag for the announcer (male/female)
                - news_original: Simplified B1-level Spanish summary

        Raises:
            GeminiSummarizerError: If there is an error in generating or parsing the response
            GeminiUnexpectedFinishReason: If the model stops generation for an unexpected reason
        """

        logger.info(f"Sending a request to Gemini to create a news summary.")

        try:
            json_str = self._generate_response(news_article)
        except GeminiUnexpectedFinishReason as e:
            return ResponseError(error=f"LLM engine responded with: {e}")
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            raise GeminiSummarizerError(f"Failed to generate response: {e}")

        try:
            summary_data = json.loads(json_str)

            return MinimalNewsSummary(
                voice_tag=summary_data["b_voice_tag"],
                news_original=summary_data["c_composed_news"]
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise GeminiSummarizerError(
                f"Failed to parse Gemini response: {e}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    api_key = settings.agent_engine_api_key
    if not api_key:
        raise GeminiSummarizerError(
            "Gemini API key not found. Please set the AGENT_ENGINE_API_KEY environment variable.")

    genai.configure(api_key=api_key)

    summarizer = Summarizer(settings.agent_engine_model)
    summary = summarizer.generate(news_article_example)

    if isinstance(summary, ResponseError):
        print(f"Error: {summary.error}")
    else:
        print("Summary Created Successfully!")
        print(f"Voice Tag: {summary.voice_tag}")
        print(f"Spanish Summary: {summary.news_original}")
