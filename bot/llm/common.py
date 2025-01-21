import os
from datetime import datetime
from typing import Optional, Any

from .types import ChatModelConfig, BaseChatModelResponse, RawChatModelResponse, DeserializedChatModelResponse, BaseStructuredOutput
from .exceptions import GenerationError, UnexpectedFinishReason

class BaseChatModel:
    def __init__(self, config: ChatModelConfig):
        self._session_id = config.session_id
        self._agent_id = config.agent_id
        self._keep_raw_engine_responses = config.keep_raw_engine_responses
        self._raw_engine_responses_dir = config.raw_engine_responses_dir

        if config.response_class:
            self._response_class = config.response_class

    def _save_response(self, response: dict):
        """Save the raw response from the LLM model to a file for debugging/logging purposes.

        If enabled via settings, saves the complete model response to a timestamped file
        in a directory structure organized by session ID. The agent_id is included in the 
        filename to distinguish responses from different agents within the same session.

        Args:
            response (dict): The raw response dictionary from the Gemini model
        """

        if self._keep_raw_engine_responses:
            response_dir = os.path.join(
                self._raw_engine_responses_dir, self._session_id)
            os.makedirs(response_dir, exist_ok=True)
            file_path = os.path.join(
                response_dir,
                f"{self._agent_id}_{
                    datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
            )
            with open(file_path, "w") as f:
                f.write(str(response))

    def _generate_response(self, prompt: str, response_class: Optional[Any] = None) -> BaseChatModelResponse:
        pass

    def _deserialize_response(self, response: str, response_class: BaseStructuredOutput) -> BaseStructuredOutput:
        pass

    def generate_response(self, prompt: str, response_class: BaseStructuredOutput = None) -> BaseChatModelResponse:
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
            if res.failure_reason[0] == "Error generating response":
                raise GenerationError(f"{res.failure_reason[0]}: {res.failure_reason[1]}")
            else:
                raise UnexpectedFinishReason(res.failure_reason[1])    
