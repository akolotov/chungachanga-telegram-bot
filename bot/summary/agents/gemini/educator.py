import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content
import logging
import json
from typing import Union

from ...models import NewsContent, EducatingVocabularyItem, NewsSummary, ResponseError
from .prompts import system_prompt_educator as system_prompt
from .prompts import news_article_example, news_without_acronyms_example
from .base import BaseChatModel, ChatModelConfig
from .educator_helper import filter_vocabulary
from .exceptions import GeminiEducatorError, GeminiUnexpectedFinishReason
from bot.settings import settings

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
    """Gemini-powered agent that processes Spanish news content for language learners.
    
    This class extends BaseChatModel to provide educational content processing, including:
    - Translation of Spanish news summaries to the target language
    - Identification and translation of key vocabulary
    - CEFR level assessment of Spanish words
    - Generation of synonyms for translations
    
    The agent uses a structured prompt to ensure consistent output formatting and
    leverages the Gemini model's capabilities for language understanding and generation.
    
    Attributes:
        target_language (str): The language to translate content into (e.g., "Russian")
    """

    def __init__(self, model_name: str, session_id: str, target_language: str = "Russian"):
        """Initialize the Educator agent with specific configuration.
        
        Args:
            model_name (str): Name of the Gemini model to use
            session_id (str): Unique identifier to track agents' responses belong to the same session
            target_language (str, optional): Target language for translations. Defaults to "Russian"
        
        The initialization:
        1. Sets up the response schema for structured output
        2. Configures the system prompt with the target language
        3. Initializes the base chat model with the specified configuration
        """

        logger.info(f"Using Gemini model {model_name}.")

        formatted_system_prompt = system_prompt.format(
            language=target_language
        )

        model_config = ChatModelConfig(
            session_id=session_id,
            agent_id="educator",
            llm_model_name=model_name,
            temperature=0.2,
            system_prompt=formatted_system_prompt,
            response_schema=educating_item_schema,
            max_tokens=1500
        )
        super().__init__(model_config)
    
    def translate(self, news_content: NewsContent) -> Union[NewsSummary, ResponseError]:
        """Process and translate news content for language learners.
        
        This method takes Spanish news content and:
        1. Identifies key vocabulary words
        2. Assesses CEFR levels for Spanish words
        3. Provides translations and synonyms
        4. Translates the full summary
        
        Args:
            news_content (NewsContent): Object containing original article and summary in Spanish
        
        Returns:
            NewsSummary: Processed content including translations, vocabulary, and analysis
            ResponseError: If there's an error in model generation
        
        Raises:
            GeminiModelError: If there's an error in model generation
            GeminiUnexpectedFinishReason: If the model stops generation unexpectedly
        """

        logger.info(f"Sending a request to Gemini to translate a news article.")

        try:
            json_str = self._generate_response(news_content.model_dump_json())
        except GeminiUnexpectedFinishReason as e:
            return ResponseError(error=f"LLM engine responded with: {e}")
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

    if isinstance(translated_summary, ResponseError):
        print(f"Error: {translated_summary.error}")
    else:
        print("Summary Created Successfully!")
        print(f"Translated Summary: {translated_summary.news_translated}")
        print(f"Vocabulary: {translated_summary.vocabulary}")
