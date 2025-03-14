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

from .exceptions import GeminiClassifierError
from .prompts.relation import (
    classifier_prompt,
    classifier_structured_output
)
from . import agents_config
from .types import ArticleRelation

logger = get_component_logger("downloader.agent.classifier")

class ClassifiedArticle(BaseStructuredOutput):
    """Structured output for article classification."""
    relation: ArticleRelation

    @classmethod
    def llm_schema(cls, _engine: LLMEngine) -> content.Schema:
        return classifier_structured_output

    @classmethod
    def deserialize(cls, json_str: str, _engine: LLMEngine) -> "ClassifiedArticle":
        """Deserialize the LLM response into a ClassifiedArticle object."""
        try:
            classification_data = json.loads(json_str)
            relation_value = classification_data["b_related"]

            return ClassifiedArticle(
                relation=ArticleRelation(relation_value)
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise DeserializationError(f"Failed to parse Gemini response: {e}")

class Classifier(GeminiChatModel):
    """Gemini-powered agent that classifies whether news articles are related to Costa Rica.
    
    This class extends GeminiChatModel to provide article classification functionality:
    - Analyzes the article content
    - Determines if the article is directly, indirectly, or not related to Costa Rica
    
    The agent uses a structured prompt to ensure consistent output formatting and
    leverages the Gemini model's capabilities for text analysis and classification.
    """

    def __init__(self, session_id: str = ""):
        """Initialize the Classifier agent with specific configuration.
        
        Args:
            session_id (str): Unique identifier to track agents' responses belong to the same session
        """
        config = agents_config.classifier
        model_config = ChatModelConfig(
            session_id=session_id,
            agent_id="classifier",
            llm_model_name=config.llm_model_name,
            temperature=config.temperature,
            system_prompt=classifier_prompt,
            response_class=ClassifiedArticle,
            max_tokens=config.max_tokens,
            keep_raw_engine_responses=config.keep_raw_engine_responses,
            raw_engine_responses_dir=config.raw_engine_responses_dir,
            request_limit=config.request_limit,
            request_limit_period_seconds=config.request_limit_period_seconds,
            support_model_config=config.supplementary_model_config,
            logger=logger
        )
        super().__init__(model_config)

    def process(self, article: str) -> Union[ClassifiedArticle, BaseResponseError]:
        """Process and classify a news article's relation to Costa Rica.
        
        This method takes news content and:
        1. Analyzes the article content
        2. Determines if the article is directly, indirectly, or not related to Costa Rica
        
        Args:
            article (str): The news article to classify
        
        Returns:
            Union[ClassifiedArticle, BaseResponseError]: Either a ClassifiedArticle object containing:
                - relation (ArticleRelation): The classification result (DIRECTLY, INDIRECTLY, or NOT_APPLICABLE)
            Or a BaseResponseError if the classification fails
        """
        logger.info(f"Sending a request to Gemini to classify a news article.")

        try:
            model_response = self.generate_response(article)
        except UnexpectedFinishReason as e:
            return BaseResponseError(error=f"LLM engine responded with: {e}")
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            raise GeminiClassifierError(f"Failed to generate response: {e}")

        return model_response.response

if __name__ == "__main__":
    from datetime import datetime
    from bot.llm import initialize
    from .prompts.tests import test_article, test_article_relation_na

    # Initialize LLM
    initialize()

    # Create session ID
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Test classification
    classifier_directly = Classifier(session_id)
    result = classifier_directly.process(test_article)

    if isinstance(result, BaseResponseError):
        print(f"Error: {result.error}")
    else:
        print("\nClassification Results:")
        print(f"Relation to Costa Rica: {result.relation}")

    classifier_na = Classifier(session_id)
    result = classifier_na.process(test_article_relation_na)

    if isinstance(result, BaseResponseError):
        print(f"Error: {result.error}")
    else:
        print("\nClassification Results:")
        print(f"Relation to Costa Rica: {result.relation}")
