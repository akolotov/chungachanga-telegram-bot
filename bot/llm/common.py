import os
from datetime import datetime
from typing import Optional, Any

from .types import ChatModelConfig, BaseChatModelResponse, RawChatModelResponse, DeserializedChatModelResponse, BaseStructuredOutput
from .exceptions import GenerationError, UnexpectedFinishReason

class BaseChatModel:
    """Base class for chat model implementations.

    This class provides common functionality for chat model implementations including:
    - Response saving/logging
    - Response generation and deserialization

    Chat models for specific LLM engines should inherit from this class and implement:
    - _generate_response(): Generate a response from the LLM
    - _deserialize_response(): Parse raw responses into structured objects

    Attributes:
        _llm_name (str): Name of the LLM model being used
        _response_class (Optional[Any]): Class for structured response parsing
        _session_id (str): ID of the session for organizing raw responses from different agents
        _agent_id (str): ID of the agent within the session to keep raw responses of one agent in the same file
        _keep_raw_engine_responses (bool): Whether to save raw model responses
        _raw_engine_responses_dir (str): Directory to save response files
    """
    def __init__(self, config: ChatModelConfig):
        self._session_id = config.session_id
        self._agent_id = config.agent_id
        self._llm_name = config.llm_model_name
        self._keep_raw_engine_responses = config.keep_raw_engine_responses
        self._raw_engine_responses_dir = config.raw_engine_responses_dir

        if config.response_class:
            self._response_class = config.response_class

    def _save_response(self, response: dict) -> Optional[str]:
        """Save the raw response from the LLM model to a file for debugging/logging purposes.

        If enabled via settings, saves the complete model response to a timestamped file
        in a directory structure organized by session ID. The agent_id is included in the 
        filename to distinguish responses from different agents within the same session.
        
        If self._raw_response_filepath is set, that path will be used instead of generating one.

        Args:
            response (dict): The raw response dictionary from the Gemini model

        Returns:
            Optional[str]: The path to the saved file if successful, otherwise None
        """

        if self._keep_raw_engine_responses:
            # Use provided file path if available, otherwise generate one
            if hasattr(self, '_raw_response_filepath') and self._raw_response_filepath:
                file_path = self._raw_response_filepath
            else:
                response_dir = os.path.join(
                    self._raw_engine_responses_dir, self._session_id)
                file_path = os.path.join(
                    response_dir,
                    f"{self._agent_id}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
                )
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, "a") as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {self._llm_name} response:\n")
                f.write(str(response))
                f.write("\n\n")
            
            return file_path
        else:
            return None

    @property
    def raw_response_filepath(self) -> Optional[str]:
        """Get the current filepath to save raw LLM responses to."""
        return self._raw_response_filepath if hasattr(self, '_raw_response_filepath') else None
    
    @raw_response_filepath.setter
    def raw_response_filepath(self, filepath: Optional[str]):
        """Set the filepath where raw LLM responses will be saved.
        
        Args:
            filepath: The filepath to save responses to, or None to use the default path generation
        """
        self._raw_response_filepath = filepath

    def _generate_response(self, prompt: str, response_class: Optional[Any] = None) -> BaseChatModelResponse:
        pass

    def _deserialize_response(self, response: str, response_class: BaseStructuredOutput) -> BaseStructuredOutput:
        pass

    @property
    def llm_name(self) -> str:
        """Get the name of the LLM model."""
        return self._llm_name
    
    def generate_response(self, prompt: str, response_class: BaseStructuredOutput = None) -> BaseChatModelResponse:
        """Generate a response from the LLM model.

        Args:
            prompt (str): The prompt to generate a response for
            response_class (BaseStructuredOutput): The response class to deserialize the response into

        Returns:
            BaseChatModelResponse: The response from the LLM model
        """
        if response_class is not None and response_class:
            # response class could be specified for particular prompt
            res = self._generate_response(prompt, response_class=response_class)
        else:
            # either the response class is specified for all prompts for the model during initialization
            # or it is assumed that response is not structured
            res = self._generate_response(prompt)

        if res.success:
            if response_class:
                # if response class is specified for the particular prompt, deserialize the response
                return DeserializedChatModelResponse(
                    success=True,
                    response=self._deserialize_response(res.response, response_class)
                )
            else:
                if hasattr(self, '_response_class'):
                    # if response class is not specified for the particular prompt, it could be still specified for the model
                    # in which case, deserialize the response
                    return DeserializedChatModelResponse(
                        success=True,
                        response=self._deserialize_response(res.response, self._response_class)
                    )
                else:
                    # if the response class is not specified neither for the particular prompt nor for the model,
                    # return the raw response
                    return RawChatModelResponse(
                        success=True,
                        response=res.response
                    )
        else:
            if res.failure_reason[0] == "Unexpected finish reason":
                raise UnexpectedFinishReason(res.failure_reason[1])
            else:
                raise GenerationError(f"{res.failure_reason[0]}: {res.failure_reason[1]}")
