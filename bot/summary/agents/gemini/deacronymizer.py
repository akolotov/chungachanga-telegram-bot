# Python standard library imports
import json
import logging
from typing import Union

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

from .exceptions import GeminiDeacronymizerError
from .prompts import (
    news_article_example,
    news_summary_example,
    system_prompt_deacronymizer as system_prompt,
)
from ...models import NewsContent, ResponseError

logger = logging.getLogger(__name__)


class DeacronymizedSummary(BaseStructuredOutput):
    summary: str

    @classmethod
    def llm_schema(cls, _engine: LLMEngine) -> content.Schema:
        return content.Schema(
            type=content.Type.OBJECT,
            required=["chain_of_thought", "acronyms", "summary"],
            properties={
                "chain_of_thought": content.Schema(
                    type=content.Type.STRING,
                ),
                "acronyms": content.Schema(
                    type=content.Type.ARRAY,
                    items=content.Schema(
                        type=content.Type.OBJECT,
                        required=["acronym", "full_form"],
                        properties={
                            "acronym": content.Schema(type=content.Type.STRING),
                            "full_form": content.Schema(type=content.Type.STRING),
                        },
                    ),
                ),
                "summary": content.Schema(
                    type=content.Type.STRING,
                ),
            },
        )

    @classmethod
    def deserialize(cls, json_str: str, _engine: LLMEngine) -> "DeacronymizedSummary":
        try:
            deacronymization_analysis = json.loads(json_str)

            return DeacronymizedSummary(
                summary=deacronymization_analysis["summary"]
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise DeserializationError(
                f"Failed to parse Gemini response: {e}")


class Deacronymizer(GeminiChatModel):
    """A class for converting acronyms in Spanish news summaries to their full forms.

    This class uses the Gemini model to identify and expand acronyms in news summaries,
    making them more accessible to non-native Spanish speakers. It inherits from BaseChatModel
    and uses the system prompt defined in prompts.py.

    The class processes NewsContent objects and returns DeacronymizedItem objects
    containing the identified acronyms, their full forms, and the updated summary.

    Attributes:
        Inherits all attributes from BaseChatModel
    """

    def __init__(self, model_name: str, session_id: str = ""):
        """Initialize the Deacronymizer with configuration for acronym processing.

        Args:
            model_name (str): Name of the Gemini model to use
            session_id (str): Unique identifier to track agents' responses belong to the same session
        """

        logger.info(f"Using Gemini model {model_name}.")
        model_config = ChatModelConfig(
            session_id=session_id,
            agent_id="deacronymizer",
            llm_model_name=model_name,
            temperature=0.2,
            system_prompt=system_prompt,
            response_class=DeacronymizedSummary,
            max_tokens=8192,
            keep_raw_engine_responses=settings.keep_raw_engine_responses,
            raw_engine_responses_dir=settings.raw_engine_responses_dir
        )
        super().__init__(model_config)

    def sanitize(self, news_content: NewsContent) -> Union[str, ResponseError]:
        """Process a news summary to expand all acronyms to their full forms.

        Takes a NewsContent object containing the original article and its summary,
        identifies any acronyms present, and returns a string with the expanded
        version of the summary where acronyms replaced by full forms

        Args:
            news_content (NewsContent): Object containing the original article and its summary,
                both in Spanish.

        Returns:
            String with updated text with acronyms replaced by full forms or ResponseError:
        """

        logger.info(
            f"Sending a request to Gemini to deacronymize a news article.")

        try:
            model_response = self.generate_response(news_content.model_dump_json())
        except UnexpectedFinishReason as e:
            return ResponseError(error=f"LLM engine responded with: {e}")
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            raise GeminiDeacronymizerError(f"Failed to generate response: {e}")

        return model_response.response.summary


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    from bot.llm import initialize

    api_key = settings.agent_engine_api_key
    if not api_key:
        raise GeminiDeacronymizerError(
            "Gemini API key not found. Please set the AGENT_ENGINE_API_KEY environment variable.")

    initialize()

    deacronymizer = Deacronymizer(settings.agent_engine_model)
    sanitized_summary = deacronymizer.sanitize(
        NewsContent(
            original_article=news_article_example,
            summary=news_summary_example
        )
    )

    if isinstance(sanitized_summary, ResponseError):
        print(f"Error: {sanitized_summary.error}")
    else:
        print("Summary Created Successfully!")
        print(f"Sanitized Summary: {sanitized_summary}")
