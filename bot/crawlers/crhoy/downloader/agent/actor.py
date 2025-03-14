"""Agent actor functionality for news processing."""

from datetime import datetime
from typing import Dict, Union

from bot.llm import BaseResponseError
from ...common.logger import get_component_logger
from .summarizer import Summarizer
from .translator import Translator
from .exceptions import GeminiBaseError
from .types import ActorWorkItem, ArticleSummary, ArticleCategory, ArticleRelation
from .classifier import Classifier
from .labeler import Labeler
from .namer import Namer
from .label_finalizer import LabelFinalizer
from .prompts.category import UNKNOWN_CATEGORY, UNKNOWN_CATEGORY_DESCRIPTION

logger = get_component_logger("downloader.agent.actor")

def categorize_article(article: str, existing_categories: Dict[str, str], session_id: str = "") -> Union[ArticleCategory, BaseResponseError]:
    """Process a Spanish news article to determine its category using a multi-agent pipeline.

    This function orchestrates a four-stage process:
    1. Classification: Determines if the article is related to Costa Rica
    2. Labeling: Identifies potential existing categories that match the article
    3. Naming: Suggests a new category if needed
    4. Finalization: Decides between existing and new categories

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
        
        # Step 1: Classify the article's relation to Costa Rica
        classifier = Classifier(session_id)
        classification_result = classifier.process(article)
        if isinstance(classification_result, BaseResponseError):
            return classification_result
        
        # If the article is not related to Costa Rica, return with UNKNOWN_CATEGORY
        if classification_result.relation == ArticleRelation.NOT_APPLICABLE:
            return ArticleCategory(
                related=classification_result.relation,
                category=UNKNOWN_CATEGORY,
                category_description=UNKNOWN_CATEGORY_DESCRIPTION
            )
        
        # Step 2: Label the article with existing categories
        labeler = Labeler(existing_categories, session_id)
        labeling_result = labeler.process(article)
        if isinstance(labeling_result, BaseResponseError):
            return labeling_result
        
        # Check if there's a category with rank > 95
        high_rank_category = None
        for suggestion in labeling_result.suggested_categories:
            if suggestion.rank > 95:
                high_rank_category = suggestion
                break
        
        if high_rank_category:
            return ArticleCategory(
                related=classification_result.relation,
                category=high_rank_category.category,
                category_description=existing_categories.get(high_rank_category.category, "")
            )
        
        # Step 3: Generate a new category suggestion that might be more appropriate
        # Initialize Namer agent to suggest a potentially better category
        namer = Namer(session_id)
        naming_result = namer.process(article)
        if isinstance(naming_result, BaseResponseError):
            return naming_result
            
        if labeling_result.no_category:
            return ArticleCategory(
                related=classification_result.relation,
                category=naming_result.category_name,
                category_description=naming_result.description
            )
        
        # Step 4: Finalize the category selection
        # Extract only the categories suggested by the Labeler
        suggested_categories = {}
        for suggestion in labeling_result.suggested_categories:
            category = suggestion.category
            if category in existing_categories:
                suggested_categories[category] = existing_categories[category]
        
        # Use label finalizer to decide between existing and new category
        finalizer = LabelFinalizer(
            suggested_categories,
            (naming_result.category_name, naming_result.description),
            session_id
        )
        
        finalization_result = finalizer.process(article)
        if isinstance(finalization_result, BaseResponseError):
            return finalization_result
        
        # Determine the category description based on whether a new category was chosen
        category_description = ""
        if finalization_result.new_chosen:
            category_description = naming_result.description
        else:
            category_description = existing_categories.get(finalization_result.category, "")
        
        return ArticleCategory(
            related=classification_result.relation,
            category=finalization_result.category,
            category_description=category_description
        )

    except GeminiBaseError as e:
        logger.error(f"Unexpected error during categorization: {str(e)}")
        raise GeminiBaseError(f"Unexpected error during categorization: {str(e)}")

def summarize_article(article: str, target_language: str, session_id: str = "") -> Union[ArticleSummary, BaseResponseError]:
    """Process a Spanish news article through a multi-agent pipeline to create a summary.

    This function orchestrates a two-stage process:
    1. Summarization: Creates a concise English summary of the article
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
        summary = summarizer.process(article)
        if isinstance(summary, BaseResponseError):
            return summary

        # Translate the summary
        translator = Translator(target_language, session_id)
        translated_summary = translator.translate(
            ActorWorkItem(
                original_article=article,
                summary=summary.news_summary
            )
        )
        if isinstance(translated_summary, BaseResponseError):
            return translated_summary

        return ArticleSummary(
            summary=summary.news_summary,
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