import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content
import logging
import json
from typing import Union

from ...models import NewsSummaryVerification, NewsContent, ResponseError
from .prompts import system_prompt_summary_verification as system_prompt
from .prompts import news_article_example, news_summary_example
from .base import BaseChatModel, ChatModelConfig
from .exceptions import GeminiSummarizerVerificationError, GeminiUnexpectedFinishReason
from bot.settings import settings

logger = logging.getLogger(__name__)

summary_verification_schema = content.Schema(
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

class SummaryVerifier(BaseChatModel):
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
            response_schema=summary_verification_schema,
            max_tokens=8192
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
            Union[NewsSummaryVerification, ResponseError]: Either:
                - NewsSummaryVerification: Object containing:
                    - adjustments_required: Boolean indicating if changes are needed
                    - composed_news: Adjusted summary text or empty if no changes needed
                - ResponseError: Error details if the verification fails

        Raises:
            GeminiSummarizerVerificationError: If there is an error in generating or parsing the response
            GeminiUnexpectedFinishReason: If the model stops generation for an unexpected reason
        """
        logger.info(f"Sending a request to Gemini to verify a news summary.")

        try:
            json_str = self._generate_response(news_content.model_dump_json())
        except GeminiUnexpectedFinishReason as e:
            return ResponseError(error=f"LLM engine responded with: {e}")
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            raise GeminiSummarizerVerificationError(
                f"Failed to generate response: {e}")

        try:
            summary_data = json.loads(json_str)

            return NewsSummaryVerification(
                adjustments_required=summary_data["b_adjustments_required"],
                composed_news=summary_data["c_composed_news"]
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise GeminiSummarizerVerificationError(
                f"Failed to parse Gemini response: {e}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    api_key = settings.agent_engine_api_key
    if not api_key:
        raise GeminiSummarizerVerificationError(
            "Gemini API key not found. Please set the AGENT_ENGINE_API_KEY environment variable.")

    genai.configure(api_key=api_key)

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
