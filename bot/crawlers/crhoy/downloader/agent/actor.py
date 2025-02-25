"""Agent actor functionality for news processing."""

from datetime import datetime
from typing import Dict, Union

from bot.llm import BaseResponseError
from ...common.logger import get_component_logger
from .categorizer import Categorizer
from .summarizer import Summarizer
from .summary_verifier import SummaryVerifier
from .translator import Translator
from .exceptions import GeminiBaseError
from .types import ActorWorkItem, ArticleSummary, ArticleCategory

logger = get_component_logger("downloader.agent.actor")

def categorize_article(article: str, existing_categories: Dict[str, str], session_id: str = "") -> Union[ArticleCategory, BaseResponseError]:
    """Process a Spanish news article to determine its category.

    Args:
        article (str): The original Spanish news article text to be processed
        existing_categories (Dict[str, str]): Dictionary of existing categories and their descriptions
        session_id (str): Unique identifier to track related agent responses belonging to the same session

    Returns:
        Union[ArticleCategory, BaseResponseError]: Either an ArticleCategory object containing:
            - related (str): Whether the article is related to Costa Rica ("directly", "indirectly", "na")
            - category (str): The determined category for the article
            - category_description (str): Description of the category if it's a new one
        Or a BaseResponseError if any stage fails.

    Raises:
        GeminiBaseError: If an unexpected error occurs during the categorization process
    """

    try:
        if not session_id:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        categorizer = Categorizer(existing_categories, session_id)
        categorization = categorizer.process(article)
        if isinstance(categorization, BaseResponseError):
            return categorization

        return ArticleCategory(
            related=categorization.related,
            category=categorization.category,
            category_description=categorization.category_description
        )

    except GeminiBaseError as e:
        logger.error(f"Unexpected error during categorization: {str(e)}")
        raise GeminiBaseError(f"Unexpected error during categorization: {str(e)}")

def summarize_article(article: str, target_language: str, session_id: str = "") -> Union[ArticleSummary, BaseResponseError]:
    """Process a Spanish news article through a multi-stage pipeline to create a summary.

    This function orchestrates a three-stage process:
    1. Summarization & Verification: Creates and verifies a concise summary
    2. Translation: Translates the summary to the target language

    Args:
        article (str): The original Spanish news article text to be processed
        target_language (str): Target language for the translation
        session_id (str): Unique identifier to track related agent responses belonging to the same session

    Returns:
        Union[ArticleSummary, BaseResponseError]: Either an ArticleSummary object containing:
            - summary (str): Original English summary
            - translated_summary (str): Translated summary in the target language
        Or a BaseResponseError if any stage fails.

    Raises:
        GeminiBaseError: If an unexpected error occurs during the summarization process
    """

    try:
        if not session_id:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Generate initial summary
        summarizer = Summarizer(session_id)
        initial_summary = summarizer.process(article)
        if isinstance(initial_summary, BaseResponseError):
            return initial_summary

        # Verify and potentially adjust the summary
        verifier = SummaryVerifier(session_id)
        verification_result = verifier.verify(
            ActorWorkItem(
                original_article=article,
                summary=initial_summary.news_summary
            )
        )
        if isinstance(verification_result, BaseResponseError):
            return verification_result

        # Use verified/adjusted summary
        final_summary = verification_result.news_summary if verification_result.adjustments_required else initial_summary.news_summary

        # Translate the summary
        translator = Translator(target_language, session_id)
        translated_summary = translator.translate(
            ActorWorkItem(
                original_article=article,
                summary=final_summary
            )
        )
        if isinstance(translated_summary, BaseResponseError):
            return translated_summary

        return ArticleSummary(
            summary=final_summary,
            translated_summary=translated_summary.translated_summary
        )

    except GeminiBaseError as e:
        logger.error(f"Unexpected error during summarization: {str(e)}")
        raise GeminiBaseError(f"Unexpected error during summarization: {str(e)}")

if __name__ == "__main__":
    from bot.llm import initialize
    from .prompts.category import initial_existing_categories_to_map
    from .prompts.tests import test_article

    initialize()

    # Test categorization
    category_result = categorize_article(test_article, initial_existing_categories_to_map())
    if isinstance(category_result, BaseResponseError):
        print(f"Error: {category_result.error}")
    else:
        print("Category Results:")
        print(f"Related: {category_result.related}")
        print(f"Category: {category_result.category}")
        print(f"Description: {category_result.category_description}")

    # Test summarization
    summary_result = summarize_article(test_article, "Russian")
    if isinstance(summary_result, BaseResponseError):
        print(f"Error: {summary_result.error}")
    else:
        print("\nSummary Results:")
        print(f"English Summary: {summary_result.summary}")
        print(f"Russian Translation: {summary_result.translated_summary}") 