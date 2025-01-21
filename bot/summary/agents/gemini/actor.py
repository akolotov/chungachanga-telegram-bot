from datetime import datetime
import logging
from typing import Union

from bot.llm import initialize
from .summary_router import SummaryRouter
from .deacronymizer import Deacronymizer
from .educator import Educator
from .exceptions import GeminiBaseError
from .prompts import news_article_example
from ...models import NewsContent, NewsSummary, ResponseError
from bot.settings import settings

logger = logging.getLogger(__name__)

def summarize_article(article: str, session_id: str = "") -> Union[NewsSummary, ResponseError]:
    """Process a Spanish news article through a multi-stage pipeline to create an educational summary.

    This function orchestrates a three-stage process:
    1. Summarization & Verification: Creates and verifies a concise B1-level Spanish summary
    2. Deacronymization: Expands any acronyms in the summary to their full forms
    3. Educational Processing: Translates the summary and provides vocabulary assistance

    Args:
        article (str): The original Spanish news article text to be processed
        session_id (str): Unique identifier to track related agent responses belonging to the same session

    Returns:
        Union[NewsSummary, ResponseError]: Either a NewsSummary object containing:
            - voice_tag (Literal['male', 'female']): Gender tag for TTS
            - news_original (str): Original Spanish summary
            - news_translated (str): Translated summary in target language
            - vocabulary (List[VocabularyItem]): Key vocabulary with translations
        Or a ResponseError if any stage fails.

    Raises:
        GeminiBaseError: If an unexpected error occurs during the summarization process

    Example:
        >>> result = summarize_article(
        ...     article="Un largo artículo de noticias...",
        ...     target_language="Russian",
        ...     session_id="unique_session_123"
        ... )
        >>> if isinstance(result, NewsSummary):
        ...     print(f"Summary created: {result.news_translated}")
        ... else:
        ...     print(f"Error: {result.error}")
    """

    initialize()

    try:
        if not session_id:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        router = SummaryRouter(settings.agent_engine_model, session_id)
        minimal_summary = router.process(article)
        if isinstance(minimal_summary, ResponseError):
            return minimal_summary

        deacronymizer = Deacronymizer(settings.agent_engine_model, session_id)
        news_summary = deacronymizer.sanitize(
            NewsContent(
                original_article=article,
                summary=minimal_summary.news_original
            )
        )
        if isinstance(news_summary, ResponseError):
            return news_summary

        educator = Educator(settings.agent_engine_model, session_id)
        translated_summary = educator.translate(
            NewsContent(
                original_article=article,
                summary=news_summary
            )
        )
        if isinstance(translated_summary, ResponseError):
            return translated_summary

    except GeminiBaseError as e:
        logger.error(f"Unexpected error during summarization: {str(e)}")
        raise GeminiBaseError(f"Unexpected error during summarization: {str(e)}")

    return NewsSummary(
        voice_tag=minimal_summary.voice_tag,
        news_original=news_summary,
        news_translated=translated_summary.news_translated,
        vocabulary=translated_summary.vocabulary
    )

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    summary = summarize_article(news_article_example)
    if isinstance(summary, ResponseError):
        print(f"Error: {summary.error}")
    else:
        print("Summary Created Successfully!")
        print(f"Voice Tag: {summary.voice_tag}")
        print(f"Spanish Summary: {summary.news_original}")
        print(f"Russian Translation: {summary.news_translated}")
        print("Vocabulary:")
        for item in summary.vocabulary:
            print(f"  {item.word}: {item.translation}")
