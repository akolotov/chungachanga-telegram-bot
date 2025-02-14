import json
from typing import Dict, Union

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

from .exceptions import GeminiCategorizerError
from .prompts.category import (
    categorizer_prompt,
    categorizer_structured_output
)
from .types import ArticleRelation
from . import agents_config

logger = get_component_logger("downloader.agent.categorizer")

class CategorizedArticle(BaseStructuredOutput):
    """Structured output for article categorization."""
    related: ArticleRelation
    category: str
    category_description: str

    @classmethod
    def llm_schema(cls, _engine: LLMEngine) -> content.Schema:
        return categorizer_structured_output

    @classmethod
    def deserialize(cls, json_str: str, _engine: LLMEngine) -> "CategorizedArticle":
        """Deserialize the LLM response into a CategorizedArticle object."""
        try:
            categorization_data = json.loads(json_str)

            return CategorizedArticle(
                related=ArticleRelation(categorization_data["b_related"]),
                category=categorization_data["h_category"],
                category_description=categorization_data["i_category_description"]
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise DeserializationError(f"Failed to parse Gemini response: {e}")

class Categorizer(GeminiChatModel):
    """Gemini-powered agent that categorizes Spanish news articles.
    
    This class extends GeminiChatModel to provide article categorization functionality:
    - Determines if the article is related to Costa Rica
    - Assigns a category from existing categories or suggests a new one
    - Provides a description for new categories
    
    The agent uses a structured prompt to ensure consistent output formatting and
    leverages the Gemini model's capabilities for text analysis and categorization.
    """

    def __init__(self, categories: Dict[str, str], session_id: str = ""):
        """Initialize the Categorizer agent with specific configuration.
        
        Args:
            categories (Dict[str, str]): Dictionary of existing categories and their descriptions
            session_id (str): Unique identifier to track agents' responses belong to the same session
        """
        formatted_system_prompt = categorizer_prompt.format(
            existing_categories=json.dumps(categories, indent=2)
        )

        config = agents_config.categorizer
        model_config = ChatModelConfig(
            session_id=session_id,
            agent_id="categorizer",
            llm_model_name=config.llm_model_name,
            temperature=config.temperature,
            system_prompt=formatted_system_prompt,
            response_class=CategorizedArticle,
            max_tokens=config.max_tokens,
            keep_raw_engine_responses=config.keep_raw_engine_responses,
            raw_engine_responses_dir=config.raw_engine_responses_dir,
            request_limit=config.request_limit,
            request_limit_period_seconds=config.request_limit_period_seconds,
            logger=logger
        )
        super().__init__(model_config)

    def process(self, article: str) -> Union[CategorizedArticle, BaseResponseError]:
        """Process and categorize a news article.
        
        This method takes Spanish news content and:
        1. Determines if it's related to Costa Rica
        2. Assigns an appropriate category
        3. Provides a description for new categories
        
        Args:
            article (str): The Spanish news article to categorize
        
        Returns:
            Union[CategorizedArticle, BaseResponseError]: Either a CategorizedArticle object containing:
                - related (str): Whether the article is related to Costa Rica
                - category (str): The determined category
                - category_description (str): Description if it's a new category
            Or a BaseResponseError if the categorization fails
        """
        logger.info(f"Sending a request to Gemini to categorize a news article.")

        try:
            model_response = self.generate_response(article)
        except UnexpectedFinishReason as e:
            return BaseResponseError(error=f"LLM engine responded with: {e}")
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            raise GeminiCategorizerError(f"Failed to generate response: {e}")

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

    # Test categorization
    categorizer = Categorizer(initial_existing_categories_to_map(), session_id)
    result = categorizer.process(test_article)

    if isinstance(result, BaseResponseError):
        print(f"Error: {result.error}")
    else:
        print("\nCategorization Results:")
        print(f"Related to Costa Rica: {result.related}")
        print(f"Category: {result.category}")
        print(f"Category Description: {result.category_description}") 