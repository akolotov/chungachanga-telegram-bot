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

from .exceptions import GeminiSummarizerError
from .prompts.summary import (
    summarizer_prompt,
    summarizer_structured_output
)
from . import agents_config

logger = get_component_logger("downloader.agent.summarizer")

class SummarizedArticle(BaseStructuredOutput):
    """Structured output for article summarization."""
    news_summary: str

    @classmethod
    def llm_schema(cls, _engine: LLMEngine) -> content.Schema:
        return summarizer_structured_output

    @classmethod
    def deserialize(cls, json_str: str, _engine: LLMEngine) -> "SummarizedArticle":
        """Deserialize the LLM response into a SummarizedArticle object."""
        try:
            summarization_data = json.loads(json_str)

            return SummarizedArticle(
                news_summary=summarization_data["b_news_summary"]
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise DeserializationError(f"Failed to parse Gemini response: {e}")

class Summarizer(GeminiChatModel):
    """Gemini-powered agent that summarizes Spanish news articles.
    
    This class extends GeminiChatModel to provide article summarization functionality:
    - Analyzes the article content
    - Creates a concise summary in English
    - Ensures the summary is suitable for expats aged 25-45
    
    The agent uses a structured prompt to ensure consistent output formatting and
    leverages the Gemini model's capabilities for text analysis and summarization.
    """

    def __init__(self, session_id: str = ""):
        """Initialize the Summarizer agent with specific configuration.
        
        Args:
            session_id (str): Unique identifier to track agents' responses belong to the same session
        """
        config = agents_config.summarizer
        model_config = ChatModelConfig(
            session_id=session_id,
            agent_id="summarizer",
            llm_model_name=config.llm_model_name,
            temperature=config.temperature,
            system_prompt=summarizer_prompt,
            response_class=SummarizedArticle,
            max_tokens=config.max_tokens,
            keep_raw_engine_responses=config.keep_raw_engine_responses,
            raw_engine_responses_dir=config.raw_engine_responses_dir,
            request_limit=config.request_limit,
            request_limit_period_seconds=config.request_limit_period_seconds,
            logger=logger
        )
        super().__init__(model_config)

    def process(self, article: str) -> Union[SummarizedArticle, BaseResponseError]:
        """Process and summarize a news article.
        
        This method takes Spanish news content and:
        1. Analyzes the article content
        2. Creates a concise summary in English
        
        Args:
            article (str): The Spanish news article to summarize
        
        Returns:
            Union[SummarizedArticle, BaseResponseError]: Either a SummarizedArticle object containing:
                - news_summary (str): The English summary of the article
            Or a BaseResponseError if the summarization fails
        """
        logger.info(f"Sending a request to Gemini to summarize a news article.")

        try:
            model_response = self.generate_response(article)
        except UnexpectedFinishReason as e:
            return BaseResponseError(error=f"LLM engine responded with: {e}")
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            raise GeminiSummarizerError(f"Failed to generate response: {e}")

        return model_response.response

if __name__ == "__main__":
    from datetime import datetime
    from bot.llm import initialize
    from .prompts.tests import test_article

    # Initialize LLM
    initialize()

    # Create session ID
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Test summarization
    summarizer = Summarizer(session_id)
    result = summarizer.process(test_article)

    if isinstance(result, BaseResponseError):
        print(f"Error: {result.error}")
    else:
        print("\nSummary Results:")
        print(f"English Summary: {result.news_summary}") 