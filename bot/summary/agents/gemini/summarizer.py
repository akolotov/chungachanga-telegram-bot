import os
import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content
from dotenv import load_dotenv
from ...models import MinimalNewsSummary
from .prompts import system_prompt_summarizer as system_prompt
from .prompts import news_article_example
import logging
import json
from .base import BaseChatModel
from .exceptions import GeminiSummarizerError

logger = logging.getLogger(__name__)

news_summary_schema = content.Schema(
    type=content.Type.OBJECT,
    properties={
        "MinimalNewsSummary": content.Schema(
            type=content.Type.OBJECT,
            required=["voice_tag", "news_original"],
            properties={
                "voice_tag": content.Schema(
                    type=content.Type.STRING,
                    enum=["male", "female"],
                ),
                "news_original": content.Schema(
                    type=content.Type.STRING,
                ),
            },
        ),
    },
)

class Summarizer(BaseChatModel):
    """A class to summarize news articles using Google Gemini API."""

    def __init__(self, model_name: str):
        logger.info(f"Using Gemini model {model_name}.")
        super().__init__(model_name, 1.0, system_prompt, news_summary_schema)
    
    def generate(self, news_article: str) -> MinimalNewsSummary:
        logger.info(f"Sending a request to Gemini to create a news summary.")

        try:
            json_str = self._generate_response(news_article)
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            raise GeminiSummarizerError(f"Failed to generate response: {e}")
            
        try:
            data = json.loads(json_str)
            
            summary_data = data["MinimalNewsSummary"]
            
            return MinimalNewsSummary(
                voice_tag=summary_data["voice_tag"],
                news_original=summary_data["news_original"]
            )
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise GeminiSummarizerError(f"Failed to parse Gemini response: {e}")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    load_dotenv()
    api_key = os.getenv("AGENT_ENGINE_API_KEY")
    if not api_key:
        raise GeminiSummarizerError("Gemini API key not found. Please set the AGENT_ENGINE_API_KEY environment variable.")

    model_name = os.getenv("AGENT_ENGINE_MODEL", "gemini-1.5-flash-002")

    genai.configure(api_key=api_key)

    summarizer = Summarizer(model_name)
    summary = summarizer.generate(news_article_example)

    if summary:
        print("Summary Created Successfully!")
        print(f"Voice Tag: {summary.voice_tag}")
        print(f"Spanish Summary: {summary.news_original}")
    else:
        print("Failed to create summary.")