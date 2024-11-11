import openai
from typing import Optional
from textwrap import dedent
import logging

from ...models import NewsSummary
from .prompts import system_prompt, news_article_example
from bot.settings import settings

logger = logging.getLogger(__name__)

class OpenAISummarizerError(Exception):
    """Custom exception for OpenAI Summarizer errors."""
    pass

class OpenAISummarizer:
    """A class to summarize news articles using OpenAI API."""

    def __init__(self):
        api_key = settings.agent_engine_api_key
        if not api_key:
            raise OpenAISummarizerError("OpenAI API key not found. Please set the AGENT_ENGINE_API_KEY environment variable.")

        self.model_name = settings.agent_engine_model
        logger.info(f"Using OpenAI model {self.model_name}.")

        self.model = openai.OpenAI(api_key=api_key)

    def create_news_summary(self, article: str) -> Optional[NewsSummary]:
        """
        Summarizes a news article using OpenAI API.

        Args:
            article (str): The full text of the news article to summarize.

        Returns:
            Optional[NewsSummary]: A NewsSummary object containing the summarized news in Spanish,
                                   its Russian translation, a voice tag, and a vocabulary list.
                                   Returns None if summarization fails.

        Raises:
            OpenAISummarizerError: If there's an error during the summarization process.
        """

        try:
            logger.info(f"Sending a request to OpenAI to create a news summary.")
            completion = self.model.beta.chat.completions.parse(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": dedent(system_prompt)},
                    {"role": "user", "content": article}
                ],
                temperature=1,  # Adjust for creativity vs. determinism
                max_tokens=300,    # Adjust based on expected output size
                response_format=NewsSummary,
            )

            response = completion.choices[0].message
            if response.refusal:
                raise OpenAISummarizerError(f"API refused to generate summary: {response.refusal}")
            return response.parsed

        except openai.OpenAIError as oe:
            logger.error(f"OpenAI API error: {str(oe)}")
            raise OpenAISummarizerError(f"OpenAI API error: {str(oe)}")
        except Exception as e:
            logger.error(f"Unexpected error during summarization: {str(e)}")
            raise OpenAISummarizerError(f"Unexpected error during summarization: {str(e)}")

def summarize_article(article: str, _session_id: str = "") -> Optional[NewsSummary]:
    """
    Summarizes a news article using the OpenAISummarizer.

    Args:
        article (str): The full text of the news article to summarize.

    Returns:
        Optional[NewsSummary]: A NewsSummary object containing the summarized news in Spanish,
                               its Russian translation, a voice tag, and a vocabulary list.
                               Returns None if summarization fails.
    """
    summarizer = OpenAISummarizer()
    try:
        return summarizer.create_news_summary(article)
    except OpenAISummarizerError as e:
        return None

if __name__ == "__main__":
    # Example usage

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