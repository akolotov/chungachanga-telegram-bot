import google.generativeai as genai
from .summarizer import Summarizer
from .deacronymizer import Deacronymizer
from .educator import Educator
from .exceptions import GeminiBaseError
from ...models import NewsContent, NewsSummary
import logging
from .prompts import news_article_example
from settings import settings

logger = logging.getLogger(__name__)

def summarize_article(article: str) -> NewsSummary:
    api_key = settings.agent_engine_api_key
    if not api_key:
        raise GeminiBaseError("Gemini API key not found. Please set the AGENT_ENGINE_API_KEY environment variable.")

    genai.configure(api_key=api_key)

    try:
        summarizer = Summarizer(settings.agent_engine_model)
        minimal_summary = summarizer.generate(article)

        deacronymizer = Deacronymizer(settings.agent_engine_model)
        news_summary = deacronymizer.sanitize(
            NewsContent(
                original_article=article,
                summary=minimal_summary.news_original
            )
        )

        educator = Educator(settings.agent_engine_model)
        translated_summary = educator.translate(
            NewsContent(
                original_article=article,
                summary=news_summary
            )
        )

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
    if summary:
        print("Summary Created Successfully!")
        print(f"Voice Tag: {summary.voice_tag}")
        print(f"Spanish Summary: {summary.news_original}")
        print(f"Russian Translation: {summary.news_translated}")
        print("Vocabulary:")
        for item in summary.vocabulary:
            print(f"  {item.word}: {item.translation}")
    else:
        print("Failed to create summary.")