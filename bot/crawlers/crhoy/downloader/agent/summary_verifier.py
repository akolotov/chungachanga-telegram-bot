import json
import logging
from typing import Union

from bot.llm import (
    BaseStructuredOutput,
    ChatModelConfig,
    DeserializationError,
    GeminiChatModel,
    UnexpectedFinishReason,
    BaseResponseError
)
from bot.llm.gemini import response_content as content
from bot.types import LLMEngine

from .exceptions import GeminiSummarizerVerificationError
from .prompts.verification import (
    summary_verification_prompt,
    summary_verification_structured_output
)
from .types import ActorWorkItem
from . import agents_config

logger = logging.getLogger(__name__)

class VerifiedSummary(BaseStructuredOutput):
    """Structured output for summary verification."""
    adjustments_required: bool
    news_summary: str

    @classmethod
    def llm_schema(cls, _engine: LLMEngine) -> content.Schema:
        return summary_verification_structured_output

    @classmethod
    def deserialize(cls, json_str: str, _engine: LLMEngine) -> "VerifiedSummary":
        """Deserialize the LLM response into a VerifiedSummary object."""
        try:
            verification_data = json.loads(json_str)

            return VerifiedSummary(
                adjustments_required=verification_data["b_adjustments_required"],
                news_summary=verification_data["c_news_summary"] if verification_data["b_adjustments_required"] else ""
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise DeserializationError(f"Failed to parse Gemini response: {e}")

class SummaryVerifier(GeminiChatModel):
    """Gemini-powered agent that verifies and adjusts English summaries of Spanish news articles.
    
    This class extends GeminiChatModel to provide summary verification functionality:
    - Verifies the accuracy of the English summary against the original Spanish article
    - Suggests adjustments if necessary to improve accuracy or clarity
    - Ensures the summary maintains a suitable style for the target audience
    
    The agent uses a structured prompt to ensure consistent output formatting and
    leverages the Gemini model's capabilities for text analysis and verification.
    """

    def __init__(self, session_id: str = ""):
        """Initialize the SummaryVerifier agent with specific configuration.
        
        Args:
            session_id (str): Unique identifier to track agents' responses belong to the same session
        """
        config = agents_config.verifier
        model_config = ChatModelConfig(
            session_id=session_id,
            agent_id="summary_verifier",
            llm_model_name=config.llm_model_name,
            temperature=config.temperature,
            system_prompt=summary_verification_prompt,
            response_class=VerifiedSummary,
            max_tokens=config.max_tokens,
            keep_raw_engine_responses=config.keep_raw_engine_responses,
            raw_engine_responses_dir=config.raw_engine_responses_dir,
            request_limit=config.request_limit,
            request_limit_period_seconds=config.request_limit_period_seconds
        )
        super().__init__(model_config)

    def verify(self, work_item: ActorWorkItem) -> Union[VerifiedSummary, BaseResponseError]:
        """Verify and potentially adjust a news summary.
        
        This method takes the original Spanish article and its English summary and:
        1. Verifies the accuracy of the summary
        2. Suggests adjustments if necessary
        
        Args:
            work_item (ActorWorkItem): Object containing:
                - original_article (str): The original Spanish article
                - summary (str): The English summary to verify
        
        Returns:
            Union[VerifiedSummary, BaseResponseError]: Either a VerifiedSummary object containing:
                - adjustments_required (bool): Whether adjustments were needed
                - news_summary (str): The adjusted summary if required
            Or a BaseResponseError if the verification fails
        """
        logger.info(f"Sending a request to Gemini to verify a news summary.")

        try:
            model_response = self.generate_response(work_item.model_dump_json())
        except UnexpectedFinishReason as e:
            return BaseResponseError(error=f"LLM engine responded with: {e}")
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            raise GeminiSummarizerVerificationError(f"Failed to generate response: {e}")

        return model_response.response 

if __name__ == "__main__":
    from datetime import datetime
    from bot.llm import initialize
    from .prompts.tests import test_article, test_summary
    from .types import ActorWorkItem

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    # Initialize LLM
    initialize()

    # Create session ID
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Test verification
    verifier = SummaryVerifier(session_id)
    result = verifier.verify(
        ActorWorkItem(
            original_article=test_article,
            summary=test_summary
        )
    )

    if isinstance(result, BaseResponseError):
        print(f"Error: {result.error}")
    else:
        print("\nVerification Results:")
        print(f"Adjustments Required: {result.adjustments_required}")
        if result.adjustments_required:
            print(f"Adjusted Summary: {result.news_summary}")
        else:
            print("Original summary is accurate and clear.") 