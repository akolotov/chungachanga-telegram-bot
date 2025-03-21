# Python standard library imports
from typing import Any, Optional, Tuple
import logging

# Third-party imports
from pydantic import BaseModel

# Local imports
from bot.types import LLMEngine

class SupportModelConfig(BaseModel):
    """
    Configuration for a supplementary model used to deserialize LLM responses.

    Attributes:
        llm_model_name (str): Name of the supplementary LLM model to use
        temperature (float): Controls randomness in the model's responses.
            Higher values make output more random, lower values make it more focused
        request_limit (int): Maximum number of requests allowed per time window for this model
        request_limit_period_seconds (int): Time window in seconds for the request limit
    """
    llm_model_name: str = ""
    temperature: float = None
    request_limit: int = 10  # Default: 10 requests per minute
    request_limit_period_seconds: int = 60  # Default: 60 seconds window

class ChatModelConfig(BaseModel):
    """
    Configuration for a chat model.

    Attributes:
        session_id (str): ID of the session, used to identify the session of several agents
        agent_id (str): ID of the agent, used to identify the agent in the session
        llm_model_name (str): Name of the LLM model to use
        temperature (float): Controls randomness in the model's responses. 
            Higher values (e.g., 0.8) make output more random, lower values (e.g., 0.2) make it more focused
        system_prompt (str): Initial system prompt to set model behavior and context
        response_schema (Optional[Any]): Schema defining the expected response format.
            If provided, responses will be formatted as JSON matching this schema.
            The actual type should be specified in derived configurations.
        max_tokens (Optional[int]): Maximum number of tokens in the response.
        keep_raw_engine_responses (bool): Whether to keep raw LLM responses.
        raw_engine_responses_dir (str): Directory to save raw LLM responses.
        request_limit (int): Maximum number of requests allowed per time window for this model
        request_limit_period_seconds (int): Time window in seconds for the request limit
        logger (Optional[logging.Logger]): Custom logger instance for the chat model
        support_model_config (Optional[SupportModelConfig]): Configuration for a supplementary model
            that can be used to deserialize the LLM's response into a structured output
    """
    session_id: str = ""
    agent_id: str = ""
    llm_model_name: str = ""
    temperature: float = None
    system_prompt: str = ""
    response_class: Optional[Any] = None
    max_tokens: Optional[int] = 8192
    keep_raw_engine_responses: bool = False
    raw_engine_responses_dir: str = ""
    request_limit: int = 10  # Default: 10 requests per minute
    request_limit_period_seconds: int = 60  # Default: 60 seconds window
    logger: Optional[logging.Logger] = None
    support_model_config: Optional[SupportModelConfig] = None

    class Config:
        arbitrary_types_allowed = True

class BaseChatModelResponse(BaseModel):
    success: bool
    failure_reason: Optional[Tuple[str, str]] = None
    response: Optional[Any] = None

    class Config:
        arbitrary_types_allowed = True

class RawChatModelResponse(BaseChatModelResponse):
    response: Optional[str] = None

class DeserializedChatModelResponse(BaseChatModelResponse):
    response: Optional[BaseModel] = None

class BaseStructuredOutput(BaseModel):
    @classmethod
    def llm_schema(cls, _engine: LLMEngine) -> Any:
        raise NotImplementedError("LLM schema not implemented for this response")
    
    @classmethod
    def deserialize(cls, _response: str, _engine: LLMEngine) -> "BaseStructuredOutput":
        raise NotImplementedError("Deserialization not implemented for this response")
    
class BaseResponseError(BaseModel):
    error: str
