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

from ...models import NewsContent, ResponseError
from .exceptions import GeminiSummarizerVerificationError
from .prompts import (
    news_article_example,
    news_summary_example,
    system_prompt_summary_verification as system_prompt,
)

logger = logging.getLogger(__name__)


class NewsSummaryVerification(BaseStructuredOutput):
    adjustments_required: bool
    composed_news: str

    @classmethod
    def llm_schema(cls, _engine: LLMEngine) -> content.Schema:
        return content.Schema(
            type=content.Type.OBJECT,
            enum=[],
            required=["a_chain_of_thought",
                      "b_adjustments_required", "c_composed_news"],
            properties={
                "a_chain_of_thought": content.Schema(
                    type=content.Type.STRING,
                ),
                "b_adjustments_required": content.Schema(
                    type=content.Type.BOOLEAN,
                ),
                "c_composed_news": content.Schema(
                    type=content.Type.STRING,
                ),
            },
        )

    @classmethod
    def deserialize(cls, json_str: str, _engine: LLMEngine) -> "NewsSummaryVerification":
        try:
            verification_output = json.loads(json_str)

            return NewsSummaryVerification(
                adjustments_required=verification_output["b_adjustments_required"],
                composed_news=verification_output["c_composed_news"]
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise DeserializationError(
                f"Failed to parse Gemini response: {e}")


class SummaryVerifier(GeminiChatModel):
    """A specialized chat model for verifying news summaries.

    This class extends BaseChatModel to verify news summaries.

    Inherits from:
        BaseChatModel: Base class for Gemini model interactions
    """

    def __init__(self, model_name: str, session_id: str = ""):
        """Initialize the SummaryVerifier with specific configuration for news verification.

        Args:
            model_name (str): Name of the Gemini model to use
            session_id (str): Unique identifier to track agents' responses belong to the same session
        """

        logger.info(f"Using Gemini model {model_name}.")

        model_config = ChatModelConfig(
            session_id=session_id,
            agent_id="summary_verifier",
            llm_model_name=model_name,
            temperature=1.0,
            system_prompt=system_prompt,
            response_class=NewsSummaryVerification,
            max_tokens=8192,
            keep_raw_engine_responses=settings.keep_raw_engine_responses,
            raw_engine_responses_dir=settings.raw_engine_responses_dir
        )
        super().__init__(model_config)

    def verify(self, news_content: NewsContent) -> Union[NewsSummaryVerification, ResponseError]:
        """Process and verify the accuracy of a news summary against its original article.

        Takes a NewsContent object containing both the original article and its summary,
        analyzes the summary for accuracy and completeness, and suggests adjustments
        if necessary.

        Args:
            news_content (NewsContent): Object containing the original article and its summary,
                both in Spanish.

        Returns:
            NewsSummaryVerification or ResponseError:
                - NewsSummaryVerification: Object containing:
                    - adjustments_required: Boolean indicating if changes are needed
                    - composed_news: Adjusted summary text or empty if no changes needed
                - ResponseError: Error details if the verification fails
        """
        logger.info(f"Sending a request to Gemini to verify a news summary.")

        try:
            model_response = self.generate_response(news_content.model_dump_json())
        except UnexpectedFinishReason as e:
            return ResponseError(error=f"LLM engine responded with: {e}")
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            raise GeminiSummarizerVerificationError(
                f"Failed to generate response: {e}")

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
        raise GeminiSummarizerVerificationError(
            "Gemini API key not found. Please set the AGENT_ENGINE_API_KEY environment variable.")

    initialize()

    summary_verifier = SummaryVerifier(settings.agent_engine_model)
    summary = summary_verifier.verify(NewsContent(
        original_article=news_article_example,
        summary=news_summary_example
    ))

    if isinstance(summary, ResponseError):
        print(f"Error: {summary.error}")
    else:
        print("Summary Verified Successfully!")
        print(f"Adjustments Required: {summary.adjustments_required}")
        print(f"Composed News: {summary.composed_news}")
