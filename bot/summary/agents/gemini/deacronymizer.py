import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content
import logging
import json

from ...models import NewsContent, ResponseError
from .prompts import system_prompt_deacronymizer as system_prompt
from .prompts import news_article_example, news_summary_example
from .base import BaseChatModel, ChatModelConfig
from .exceptions import GeminiDeacronymizerError, GeminiUnexpectedFinishReason
from bot.settings import settings

logger = logging.getLogger(__name__)

deacronymized_item_schema = content.Schema(
    type=content.Type.OBJECT,
    properties={
        "DeacronymizedItem": content.Schema(
            type=content.Type.OBJECT,
            required=["chain_of_thought", "acronyms", "summary"],
            properties={
                "chain_of_thought": content.Schema(
                    type=content.Type.STRING,
                ),
                "acronyms": content.Schema(
                    type=content.Type.ARRAY,
                    items=content.Schema(
                        type=content.Type.OBJECT,
                        required=["acronym", "full_form"],
                        properties={
                            "acronym": content.Schema(type=content.Type.STRING),
                            "full_form": content.Schema(type=content.Type.STRING),
                        },
                    ),
                ),
                "summary": content.Schema(
                    type=content.Type.STRING,
                ),
            },
        ),
    },
)

class Deacronymizer(BaseChatModel):
    """A class to deacronymize news articles using Google Gemini API."""

    def __init__(self, model_name: str, session_id: str = ""):
        logger.info(f"Using Gemini model {model_name}.")
        model_config = ChatModelConfig(
            session_id=session_id,
            agent_id="deacronymizer",
            llm_model_name=model_name,
            temperature=0.2,
            system_prompt=system_prompt,
            response_schema=deacronymized_item_schema,
            max_tokens=1000
        )
        super().__init__(model_config)
    
    def sanitize(self, news_content: NewsContent) -> str:
        logger.info(f"Sending a request to Gemini to deacronymize a news article.")

        try:
            json_str = self._generate_response(news_content.model_dump_json())
        except GeminiUnexpectedFinishReason as e:
            return ResponseError(error=f"LLM engine responded with: {e}")
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            raise GeminiDeacronymizerError(f"Failed to generate response: {e}")
            
        try:
            data = json.loads(json_str)
            
            deacronymized_item = data["DeacronymizedItem"]

            return deacronymized_item["summary"]
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise GeminiDeacronymizerError(f"Failed to parse Gemini response: {e}")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    api_key = settings.agent_engine_api_key
    if not api_key:
        raise GeminiDeacronymizerError("Gemini API key not found. Please set the AGENT_ENGINE_API_KEY environment variable.")

    genai.configure(api_key=api_key)

    deacronymizer = Deacronymizer(settings.agent_engine_model)
    sanitized_summary = deacronymizer.sanitize(
        NewsContent(
            original_article=news_article_example,
            summary=news_summary_example
        )
    )

    if isinstance(sanitized_summary, ResponseError):
        print(f"Error: {sanitized_summary.error}")
    else:
        print("Summary Created Successfully!")
        print(f"Sanitized Summary: {sanitized_summary}")
