# Python standard library imports
import dataclasses
import logging
from textwrap import dedent
from typing import Any, Optional

# Third-party imports
import google.generativeai as genai
import proto
from google.generativeai import protos

# Local imports
from bot.types import LLMEngine
from bot.llm.ratelimiter import RateLimiter

from ..common import BaseChatModel
from ..types import BaseStructuredOutput, ChatModelConfig, RawChatModelResponse
from .initialize import is_initialized


# From google.ai.generativelanguage_v1beta.types.Candidate
# google/ai/generativelanguage_v1beta/types/generative_service.py
class FinishReason(proto.Enum):
    r"""Defines the reason why the model stopped generating tokens.

    Values:
        FINISH_REASON_UNSPECIFIED (0):
            Default value. This value is unused.
        STOP (1):
            Natural stop point of the model or provided
            stop sequence.
        MAX_TOKENS (2):
            The maximum number of tokens as specified in
            the request was reached.
        SAFETY (3):
            The response candidate content was flagged
            for safety reasons.
        RECITATION (4):
            The response candidate content was flagged
            for recitation reasons.
        LANGUAGE (6):
            The response candidate content was flagged
            for using an unsupported language.
        OTHER (5):
            Unknown reason.
        BLOCKLIST (7):
            Token generation stopped because the content
            contains forbidden terms.
        PROHIBITED_CONTENT (8):
            Token generation stopped for potentially
            containing prohibited content.
        SPII (9):
            Token generation stopped because the content
            potentially contains Sensitive Personally
            Identifiable Information (SPII).
        MALFORMED_FUNCTION_CALL (10):
            The function call generated by the model is
            invalid.
    """
    FINISH_REASON_UNSPECIFIED = 0
    STOP = 1
    MAX_TOKENS = 2
    SAFETY = 3
    RECITATION = 4
    LANGUAGE = 6
    OTHER = 5
    BLOCKLIST = 7
    PROHIBITED_CONTENT = 8
    SPII = 9
    MALFORMED_FUNCTION_CALL = 10

class GeminiChatModelResponse(RawChatModelResponse):
    response: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True

class ChatModel(BaseChatModel):
    """A wrapper class for the Gemini generative model that maintains conversation history.

    This class provides an interface to interact with Google's Gemini model while
    maintaining the conversation history between prompts and responses.

    Attributes:
        model: The underlying Gemini generative model instance
        _history: List of conversation turns between user and model
    """

    def __init__(self, config: ChatModelConfig):
        """Initialize a new BaseChatModel instance.

        Args:
            config (ChatModelConfig): Configuration for the chat model
        """
        generation_config = genai.types.GenerationConfig(
            temperature=config.temperature if config.temperature is not None else 1.0,
            top_p=0.95,
            top_k=40,
            max_output_tokens=config.max_tokens,
        )

        if config.response_class:
            generation_config.response_schema = config.response_class.llm_schema(LLMEngine.GEMINI)
            generation_config.response_mime_type = "application/json"

        self._generation_config = generation_config
        self._logger = config.logger or logging.getLogger(self.__class__.__module__)

        model_args = {"model_name": config.llm_model_name}
        if config.system_prompt:
            model_args["system_instruction"] = config.system_prompt
        self.model = genai.GenerativeModel(**model_args)

        self._history: list[protos.Content] = []

        # Initialize rate limiter with config values
        self._rate_limiter = RateLimiter.get_instance(
            model_name=config.llm_model_name,
            max_requests=config.request_limit,
            period=config.request_limit_period_seconds
        )

        super().__init__(config)

    def _generate_response(self, prompt: str, response_class: Optional[Any] = None) -> GeminiChatModelResponse:
        """Generate a response from the model based on the given prompt.

        The prompt is added to the conversation history before generating the response.
        The response is also added to the history for context in future interactions,
        but only if generation is successful (finishes with STOP reason).
        If there's an error or unexpected finish reason, the prompt is removed from history.

        Args:
            prompt (str): The input text to send to the model

        Returns:
            GeminiChatModelResponse: The response from the Gemini model
        """
        if not is_initialized():
            self._logger.error("Gemini API not initialized. Call initialize() first.")
            return GeminiChatModelResponse(
                success=False,
                failure_reason=("Initialization Error", "Gemini API not initialized. Call initialize() first.")
            )

        # Before adding to history, check rate limit
        self._rate_limiter.acquire(logger=self._logger)

        # Add prompt to history
        prompt_content = protos.Content(
            parts=[protos.Part(text=dedent(prompt))], role="user")
        self._history.append(prompt_content)

        generation_config = dataclasses.replace(self._generation_config)
        if response_class:
            generation_config.response_schema = response_class.llm_schema(LLMEngine.GEMINI)
            generation_config.response_mime_type = "application/json"

        try:
            # Request response from model for the prompt added to history
            response = self.model.generate_content(self._history, generation_config=generation_config)
        except Exception as e:
            # Roll back the prompt from history on error to avoid keeping prompts without
            # responses in history
            self._history.pop()
            self._logger.error(f"Error generating response: {e}")
            return GeminiChatModelResponse(
                success=False,
                failure_reason=("Error generating response", str(e))
            )
        
        # Before processing the response, save it to a file as is
        self._save_response(response.candidates[0])

        # Get the finish reason for the response
        finish_reason = FinishReason(response.candidates[0].finish_reason)

        if finish_reason == FinishReason.STOP:
            # Add the response to history to be used as context in future interactions
            self._history.append(response.candidates[0].content)
            return GeminiChatModelResponse(
                success=True,
                response=response.candidates[0].content.parts[0].text
            )
        else:
            # Roll back the prompt from history on error to avoid keeping prompts without
            # responses in history
            self._history.pop()
            self._logger.error(f"Unexpected finish reason: {finish_reason.name}")
            return GeminiChatModelResponse(
                success=False,
                failure_reason=("Unexpected finish reason", finish_reason.name)
            )
        
    def _deserialize_response(self, response: str, response_class: Any) -> BaseStructuredOutput:
        return response_class.deserialize(response, LLMEngine.GEMINI)
