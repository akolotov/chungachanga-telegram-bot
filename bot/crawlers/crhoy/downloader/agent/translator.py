import json
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

from .exceptions import GeminiTranslatorError
from .prompts.translation import (
    translator_prompt,
    translator_structured_output
)
from .types import ActorWorkItem
from . import agents_config
from ...common.logger import get_component_logger

logger = get_component_logger("downloader.agent.translator")

class TranslatedSummary(BaseStructuredOutput):
    """Structured output for summary translation."""
    translated_summary: str

    @classmethod
    def llm_schema(cls, _engine: LLMEngine) -> content.Schema:
        return translator_structured_output

    @classmethod
    def deserialize(cls, json_str: str, _engine: LLMEngine) -> "TranslatedSummary":
        """Deserialize the LLM response into a TranslatedSummary object."""
        try:
            translation_data = json.loads(json_str)

            return TranslatedSummary(
                translated_summary=translation_data["translated_summary"]
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise DeserializationError(f"Failed to parse Gemini response: {e}")

class Translator(GeminiChatModel):
    """Gemini-powered agent that translates English summaries to Russian.
    
    This class extends GeminiChatModel to provide translation functionality:
    - Translates English summaries to Russian
    - Ensures translations are clear and accurate
    - Maintains the appropriate style for the target audience
    
    The agent uses a structured prompt to ensure consistent output formatting and
    leverages the Gemini model's capabilities for translation.
    """

    def __init__(self, target_language: str, session_id: str = ""):
        """Initialize the Translator agent with specific configuration.
        
        Args:
            target_language (str): Target language for translations
            session_id (str): Unique identifier to track agents' responses belong to the same session
        """
        formatted_system_prompt = translator_prompt.format(
            language=target_language
        )

        config = agents_config.translator
        model_config = ChatModelConfig(
            session_id=session_id,
            agent_id="translator",
            llm_model_name=config.llm_model_name,
            temperature=config.temperature,
            system_prompt=formatted_system_prompt,
            response_class=TranslatedSummary,
            max_tokens=config.max_tokens,
            keep_raw_engine_responses=config.keep_raw_engine_responses,
            raw_engine_responses_dir=config.raw_engine_responses_dir,
            request_limit=config.request_limit,
            request_limit_period_seconds=config.request_limit_period_seconds,
            logger=logger
        )
        super().__init__(model_config)

    def translate(self, work_item: ActorWorkItem) -> Union[TranslatedSummary, BaseResponseError]:
        """Translate a news summary to Russian.
        
        This method takes the original Spanish article and its English summary and:
        1. Translates the English summary to Russian
        2. Ensures the translation is clear and accurate
        
        Args:
            work_item (ActorWorkItem): Object containing:
                - original_article (str): The original Spanish article
                - summary (str): The English summary to translate
        
        Returns:
            Union[TranslatedSummary, BaseResponseError]: Either a TranslatedSummary object containing:
                - translated_summary (str): The Russian translation of the summary
            Or a BaseResponseError if the translation fails
        """
        logger.info(f"Sending a request to Gemini to translate a news summary.")

        try:
            model_response = self.generate_response(work_item.model_dump_json())
        except UnexpectedFinishReason as e:
            return BaseResponseError(error=f"LLM engine responded with: {e}")
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            raise GeminiTranslatorError(f"Failed to generate response: {e}")

        return model_response.response 

if __name__ == "__main__":
    from datetime import datetime
    from bot.llm import initialize
    from .prompts.tests import test_article, test_summary
    from .types import ActorWorkItem

    # Initialize LLM
    initialize()

    # Create session ID
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Test translation
    translator = Translator("Russian", session_id)
    result = translator.translate(
        ActorWorkItem(
            original_article=test_article,
            summary=test_summary
        )
    )

    if isinstance(result, BaseResponseError):
        print(f"Error: {result.error}")
    else:
        print("\nTranslation Results:")
        print(f"Original Summary: {test_summary}")
        print(f"Russian Translation: {result.translated_summary}") 