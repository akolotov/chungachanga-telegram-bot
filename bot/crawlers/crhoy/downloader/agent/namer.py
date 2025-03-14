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
from ...common.logger import get_component_logger

from .exceptions import GeminiNamerError
from .prompts.new_label import (
    namer_prompt,
    namer_structured_output
)
from . import agents_config

logger = get_component_logger("downloader.agent.namer")

class NamedCategory(BaseStructuredOutput):
    """Structured output for category naming."""
    category_name: str
    description: str

    @classmethod
    def llm_schema(cls, _engine: LLMEngine) -> content.Schema:
        return namer_structured_output

    @classmethod
    def deserialize(cls, json_str: str, _engine: LLMEngine) -> "NamedCategory":
        """Deserialize the LLM response into a NamedCategory object."""
        try:
            naming_data = json.loads(json_str)
            
            return NamedCategory(
                category_name=naming_data["b_category"],
                description=naming_data["d_category_description"]
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise DeserializationError(f"Failed to parse Gemini response: {e}")

class Namer(GeminiChatModel):
    """Gemini-powered agent that suggests new category names for news articles.
    
    This class extends GeminiChatModel to provide category naming functionality:
    - Analyzes the article content
    - Suggests a suitable category name
    - Provides a description for the suggested category
    
    The agent uses a structured prompt to ensure consistent output formatting and
    leverages the Gemini model's capabilities for text analysis and categorization.
    """

    def __init__(self, session_id: str = ""):
        """Initialize the Namer agent with specific configuration.
        
        Args:
            session_id (str): Unique identifier to track agents' responses belong to the same session
        """
        config = agents_config.namer
        model_config = ChatModelConfig(
            session_id=session_id,
            agent_id="namer",
            llm_model_name=config.llm_model_name,
            temperature=config.temperature,
            system_prompt=namer_prompt,
            response_class=NamedCategory,
            max_tokens=config.max_tokens,
            keep_raw_engine_responses=config.keep_raw_engine_responses,
            raw_engine_responses_dir=config.raw_engine_responses_dir,
            request_limit=config.request_limit,
            request_limit_period_seconds=config.request_limit_period_seconds,
            support_model_config=config.supplementary_model_config,
            logger=logger
        )
        super().__init__(model_config)

    def process(self, article: str) -> Union[NamedCategory, BaseResponseError]:
        """Process and suggest a new category name for a news article.
        
        This method takes news content and:
        1. Analyzes the article content
        2. Suggests a suitable category name
        3. Provides a description for the suggested category
        
        Args:
            article (str): The news article to analyze
        
        Returns:
            Union[NamedCategory, BaseResponseError]: Either a NamedCategory object containing:
                - category_name (str): The suggested category name
                - description (str): Description of the suggested category
            Or a BaseResponseError if the naming fails
        """
        logger.info(f"Sending a request to Gemini to suggest a category name for a news article.")

        try:
            model_response = self.generate_response(article)
        except UnexpectedFinishReason as e:
            return BaseResponseError(error=f"LLM engine responded with: {e}")
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            raise GeminiNamerError(f"Failed to generate response: {e}")

        return model_response.response

if __name__ == "__main__":
    from datetime import datetime
    from bot.llm import initialize
    from .prompts.tests import test_article

    # Initialize LLM
    initialize()

    # Create session ID
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Test category naming
    namer = Namer(session_id)
    result = namer.process(test_article)
    if isinstance(result, BaseResponseError):
        print(f"Error: {result.error}")
    else:
        print("\nCategory Naming Results:")
        print(f"Suggested Category: {result.category_name}")
        print(f"Category Description: {result.description}")
