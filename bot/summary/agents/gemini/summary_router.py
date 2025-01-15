from typing import Union
import logging
import google.generativeai as genai

from .summarizer import Summarizer
from .summary_verifier import SummaryVerifier
from ...models import NewsContent, NewsSummary, ResponseError
from .prompts import news_article_example
from .exceptions import GeminiBaseError
from bot.settings import settings

logger = logging.getLogger(__name__)

class SummaryRouter:
    """Routes the summarization process through generation and verification stages."""

    def __init__(self, model_name: str, session_id: str = ""):
        """Initialize the router with required components.

        Args:
            model_name (str): Name of the Gemini model to use
            session_id (str): Unique identifier for tracking related responses
        """
        self.model_name = model_name
        self.session_id = session_id
        self.summarizer = Summarizer(model_name, session_id)
        self.verifier = SummaryVerifier(model_name, session_id)

    def process(self, article: str) -> Union[NewsSummary, ResponseError]:
        """Process article through summarization and verification pipeline.

        Args:
            article (str): Original Spanish article text

        Returns:
            Union[NewsSummary, ResponseError]: Initial or adjusted summary, or error if process fails
        """
        # Generate initial summary
        initial_summary = self.summarizer.generate(article)
        if isinstance(initial_summary, ResponseError):
            return initial_summary

        # Verify and potentially adjust the summary
        verification_result = self.verifier.verify(
            NewsContent(
                original_article=article,
                summary=initial_summary.news_original
            )
        )
        if isinstance(verification_result, ResponseError):
            return verification_result

        # If adjustments were made, use the adjusted summary
        if verification_result.adjustments_required and verification_result.composed_news:
            initial_summary.news_original = verification_result.composed_news

        return initial_summary 

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    api_key = settings.agent_engine_api_key
    if not api_key:
        raise GeminiBaseError(
            "Gemini API key not found. Please set the AGENT_ENGINE_API_KEY environment variable.")

    genai.configure(api_key=api_key)

    router = SummaryRouter(settings.agent_engine_model)
    summary = router.process(news_article_example)

    if isinstance(summary, ResponseError):
        print(f"Error: {summary.error}")
    else:
        print("Summary Created Successfully!")
        print(f"Voice Tag: {summary.voice_tag}")
        print(f"Spanish Summary: {summary.news_original}") 