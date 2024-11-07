import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content
from ...models import NewsContent, EducatingVocabularyItem, NewsSummary
from .prompts import system_prompt_educator as system_prompt
from .prompts import news_article_example, news_without_acronyms_example
import logging
import json
from .base import BaseChatModel
from .educator_helper import filter_vocabulary
from .exceptions import GeminiEducatorError
from settings import settings

logger = logging.getLogger(__name__)

educating_item_schema = content.Schema(
    type=content.Type.OBJECT,
    properties={
        "EducatingItem": content.Schema(
            type=content.Type.OBJECT,
            required=["chain_of_thought", "translated_summary", "vocabulary"],
            properties={
                "chain_of_thought": content.Schema(
                    type=content.Type.STRING,
                ),
                "vocabulary": content.Schema(
                    type=content.Type.ARRAY,
                    items = content.Schema(
                        type = content.Type.OBJECT,
                        required = ["word", "level", "importance", "translation_language", "translation", "synonyms_language", "synonyms"],
                        properties = {
                            "word": content.Schema(
                                type = content.Type.STRING,
                            ),
                            "level": content.Schema(
                                type = content.Type.STRING,
                            ),
                            "importance": content.Schema(
                                type = content.Type.STRING,
                            ),
                            "translation_language": content.Schema(
                                type = content.Type.STRING,
                            ),
                            "translation": content.Schema(
                                type = content.Type.STRING,
                            ),
                            "synonyms_language": content.Schema(
                                type = content.Type.STRING,
                            ),
                            "synonyms": content.Schema(
                                type = content.Type.ARRAY,
                                items = content.Schema(
                                    type = content.Type.STRING,
                                ),
                            ),
                        },
                    ),
                ),
                "translated_summary": content.Schema(
                    type=content.Type.STRING,
                ),
            },
        ),
    },
)

class Educator(BaseChatModel):
    """A class to educate news articles using Google Gemini API."""

    def __init__(self, model_name: str):
        logger.info(f"Using Gemini model {model_name}.")

        formatted_system_prompt = system_prompt.format(
            language="Russian"
        )

        super().__init__(model_name, 0.2, formatted_system_prompt, educating_item_schema, max_tokens=1000)
    
    def translate(self, news_content: NewsContent) -> NewsSummary:
        logger.info(f"Sending a request to Gemini to translate a news article.")

        try:
            json_str = self._generate_response(news_content.model_dump_json())
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            raise GeminiEducatorError(f"Failed to generate response: {e}")
            
        try:
            data = json.loads(json_str)
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise GeminiEducatorError(f"Failed to parse Gemini response: {e}")

        educating_item = data["EducatingItem"]

        vocabulary = [EducatingVocabularyItem(**item) for item in educating_item["vocabulary"]]
        
        try:    
            filtered_vocabulary = filter_vocabulary(vocabulary)
        except Exception as e:
            logger.error(f"Failed to filter vocabulary: {e}")
            raise GeminiEducatorError(f"Failed to filter vocabulary: {e}")

        return NewsSummary(
            voice_tag="male",
            news_original="",
            news_translated=educating_item["translated_summary"],
            vocabulary=filtered_vocabulary
        )

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    api_key = settings.agent_engine_api_key
    if not api_key:
        raise GeminiEducatorError("Gemini API key not found. Please set the AGENT_ENGINE_API_KEY environment variable.")

    genai.configure(api_key=api_key)

    educator = Educator(settings.agent_engine_model)
    translated_summary = educator.translate(
        NewsContent(
            original_article=news_article_example,
            summary=news_without_acronyms_example
        )
    )

    if translated_summary:
        print("Summary Created Successfully!")
        print(f"Translated Summary: {translated_summary.news_translated}")
        print(f"Vocabulary: {translated_summary.vocabulary}")
    else:
        print("Failed to create summary.")