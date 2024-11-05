import os
import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content
from google.generativeai import protos
from typing import Optional
from textwrap import dedent
from dotenv import load_dotenv
from ..models import NewsSummary, VocabularyItem
from .prompts import system_prompt, news_article_example
import logging
import json

logger = logging.getLogger(__name__)

news_summary_schema = content.Schema(
    type=content.Type.OBJECT,
    properties={
        "NewsSummary": content.Schema(
            type=content.Type.OBJECT,
            required=["voice_tag", "news_original", "news_translated", "vocabulary"],
            properties={
                "voice_tag": content.Schema(
                    type=content.Type.STRING,
                    enum=["male", "female"],
                ),
                "news_original": content.Schema(
                    type=content.Type.STRING,
                ),
                "news_translated": content.Schema(
                    type=content.Type.STRING,
                ),
                "vocabulary": content.Schema(
                    type=content.Type.ARRAY,
                    items=content.Schema(
                        type=content.Type.OBJECT,
                        required=["word", "translation"],
                        properties={
                            "word": content.Schema(
                                type=content.Type.STRING,
                            ),
                            "translation": content.Schema(
                                type=content.Type.STRING,
                            ),
                        },
                    ),
                ),
            },
        ),
    },
)

class GeminiSummarizerError(Exception):
    """Custom exception for Gemini Summarizer errors."""
    pass

class GeminiSummarizer:
    """A class to summarize news articles using Google Gemini API."""

    def __init__(self):
        load_dotenv()
        api_key = os.getenv("AGENT_ENGINE_API_KEY")
        if not api_key:
            raise GeminiSummarizerError("Gemini API key not found. Please set the AGENT_ENGINE_API_KEY environment variable.")

        model_name = os.getenv("AGENT_ENGINE_MODEL", "gemini-1.5-flash-002")
        logger.info(f"Using Gemini model {model_name}.")

        genai.configure(api_key=api_key)

        self.model = genai.GenerativeModel(
            model_name,
            system_instruction=system_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,
                top_p=0.95,
                top_k=40,
                max_output_tokens=500,
                response_schema=news_summary_schema,
                response_mime_type="application/json",
            )        
        )

        self._history: list[protos.Content] = []
    
    def _generate_response(self, prompt: str) -> Optional[NewsSummary]:
        """
        Generate a response from Gemini and convert it to NewsSummary.

        Args:
            prompt (str): The input text to process.

        Returns:
            Optional[NewsSummary]: A NewsSummary object containing the processed data.
        """
        self._history.append(protos.Content(parts=[protos.Part(text=dedent(prompt))], role="user"))
        response = self.model.generate_content(self._history)
        self._history.append(response.candidates[0].content)

        try:
            # Parse JSON string from response
            json_str = response.candidates[0].content.parts[0].text
            data = json.loads(json_str)
            
            # Extract NewsSummary data
            summary_data = data["NewsSummary"]
            
            # Create and return NewsSummary object
            return NewsSummary(
                voice_tag=summary_data["voice_tag"],
                news_original=summary_data["news_original"],
                news_translated=summary_data["news_translated"],
                vocabulary=[
                    VocabularyItem(word=item["word"], translation=item["translation"])
                    for item in summary_data["vocabulary"]
                ]
            )
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise GeminiSummarizerError(f"Failed to parse Gemini response: {e}")

    def create_news_summary(self, article: str) -> Optional[NewsSummary]:
        """
        Summarizes a news article using Gemini API.

        Args:
            article (str): The full text of the news article to summarize.

        Returns:
            Optional[NewsSummary]: A NewsSummary object containing the summarized news in Spanish,
                                   its Russian translation, a voice tag, and a vocabulary list.
                                   Returns None if summarization fails.

        Raises:
            GeminiSummarizerError: If there's an error during the summarization process.
        """

        try:
            logger.info(f"Sending a request to Gemini to create a news summary.")

            return self._generate_response(article)

        except Exception as e:
            logger.error(f"Unexpected error during summarization: {str(e)}")
            raise GeminiSummarizerError(f"Unexpected error during summarization: {str(e)}")

def summarize_article(article: str) -> Optional[NewsSummary]:
    """
    Summarizes a news article using the OpenAISummarizer.

    Args:
        article (str): The full text of the news article to summarize.

    Returns:
        Optional[NewsSummary]: A NewsSummary object containing the summarized news in Spanish,
                               its Russian translation, a voice tag, and a vocabulary list.
                               Returns None if summarization fails.
    """
    summarizer = GeminiSummarizer()
    try:
        return summarizer.create_news_summary(article)
    except GeminiSummarizerError as e:
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