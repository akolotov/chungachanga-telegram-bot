import json
from dataclasses import dataclass
from typing import Dict, List, Union

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

from .exceptions import GeminiLabelerError
from .prompts.label import (
    labeler_prompt,
    labeler_structured_output
)
from . import agents_config

logger = get_component_logger("downloader.agent.labeler")

@dataclass
class CategorySuggestion:
    """Represents a category suggestion with its suitability rank."""
    category: str
    rank: int

class LabeledArticle(BaseStructuredOutput):
    """Structured output for article labeling."""
    no_category: bool
    suggested_categories: List[CategorySuggestion]

    @classmethod
    def llm_schema(cls, _engine: LLMEngine) -> content.Schema:
        return labeler_structured_output

    @classmethod
    def deserialize(cls, json_str: str, _engine: LLMEngine) -> "LabeledArticle":
        """Deserialize the LLM response into a LabeledArticle object."""
        try:
            labeling_data = json.loads(json_str)
            
            # Extract no_category flag
            no_category = labeling_data["b_no_category"]
            
            # Extract suggested categories
            categories_list = labeling_data["c_existing_categories_list"]
            suggested_categories = []
            
            for category_item in categories_list:
                category = category_item["a_category"]
                rank = int(category_item["b_rank"]) if isinstance(category_item["b_rank"], str) else category_item["b_rank"]
                suggested_categories.append(CategorySuggestion(category, rank))
            
            return LabeledArticle(
                no_category=no_category,
                suggested_categories=suggested_categories
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise DeserializationError(f"Failed to parse Gemini response: {e}")

class Labeler(GeminiChatModel):
    """Gemini-powered agent that labels news articles with appropriate categories.
    
    This class extends GeminiChatModel to provide article labeling functionality:
    - Analyzes the article content
    - Determines if the article fits into existing categories
    - Suggests up to three most suitable categories with suitability ranks
    
    The agent uses a structured prompt to ensure consistent output formatting and
    leverages the Gemini model's capabilities for text analysis and categorization.
    """

    def __init__(self, categories: Dict[str, str], session_id: str = ""):
        """Initialize the Labeler agent with specific configuration.
        
        Args:
            categories (Dict[str, str]): Dictionary of existing categories and their descriptions
            session_id (str): Unique identifier to track agents' responses belong to the same session
        """
        formatted_system_prompt = labeler_prompt.format(
            existing_categories=json.dumps(categories, indent=2)
        )

        config = agents_config.labeler
        model_config = ChatModelConfig(
            session_id=session_id,
            agent_id="labeler",
            llm_model_name=config.llm_model_name,
            temperature=config.temperature,
            system_prompt=formatted_system_prompt,
            response_class=LabeledArticle,
            max_tokens=config.max_tokens,
            keep_raw_engine_responses=config.keep_raw_engine_responses,
            raw_engine_responses_dir=config.raw_engine_responses_dir,
            request_limit=config.request_limit,
            request_limit_period_seconds=config.request_limit_period_seconds,
            support_model_config=config.supplementary_model_config,
            logger=logger
        )
        super().__init__(model_config)

    def process(self, article: str) -> Union[LabeledArticle, BaseResponseError]:
        """Process and label a news article with appropriate categories.
        
        This method takes news content and:
        1. Analyzes the article content
        2. Determines if the article fits into existing categories
        3. Suggests up to three most suitable categories with suitability ranks
        
        Args:
            article (str): The news article to label
        
        Returns:
            Union[LabeledArticle, BaseResponseError]: Either a LabeledArticle object containing:
                - no_category (bool): Whether no suitable category was found
                - suggested_categories (List[CategorySuggestion]): List of suggested categories with ranks
            Or a BaseResponseError if the labeling fails
        """
        logger.info(f"Sending a request to Gemini to label a news article.")

        try:
            model_response = self.generate_response(article)
        except UnexpectedFinishReason as e:
            return BaseResponseError(error=f"LLM engine responded with: {e}")
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            raise GeminiLabelerError(f"Failed to generate response: {e}")

        return model_response.response

if __name__ == "__main__":
    from datetime import datetime
    from bot.llm import initialize
    from .prompts.tests import test_article
    from .prompts.category import initial_existing_categories_to_map

    # Initialize LLM
    initialize()

    # Create session ID
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Test labeling
    labeler = Labeler(initial_existing_categories_to_map(), session_id)
    result = labeler.process(test_article)

    if isinstance(result, BaseResponseError):
        print(f"Error: {result.error}")
    else:
        print("\nLabeling Results:")
        print(f"No suitable category found: {result.no_category}")
        print("Suggested Categories:")
        for suggestion in result.suggested_categories:
            print(f"  - {suggestion.category} (Rank: {suggestion.rank})")
