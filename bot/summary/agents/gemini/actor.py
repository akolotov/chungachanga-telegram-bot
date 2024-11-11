from datetime import datetime
import google.generativeai as genai
import logging

from .summarizer import Summarizer
from .deacronymizer import Deacronymizer
from .educator import Educator
from .exceptions import GeminiBaseError
from .prompts import news_article_example
from ...models import NewsContent, NewsSummary, ResponseError
from bot.settings import settings

logger = logging.getLogger(__name__)

def summarize_article(article: str, session_id: str = "") -> NewsSummary | ResponseError:
    api_key = settings.agent_engine_api_key
    if not api_key:
        raise GeminiBaseError("Gemini API key not found. Please set the AGENT_ENGINE_API_KEY environment variable.")

    genai.configure(api_key=api_key)

    try:
        if not session_id:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        summarizer = Summarizer(settings.agent_engine_model, session_id)
        minimal_summary = summarizer.generate(article)
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
