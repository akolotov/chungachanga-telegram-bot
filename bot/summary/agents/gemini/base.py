import google.generativeai as genai
from google.generativeai import protos
from google.ai.generativelanguage_v1beta.types import content
from typing import Optional
from textwrap import dedent
import logging

class GeminiModelError(Exception):
    """Custom exception for Gemini Model errors."""
    pass

class BaseChatModel:
    """Base class for interacting with Google's Gemini chat models.
    
    This class provides core functionality for configuring and interacting with
    Gemini models, including handling chat history and generating responses.
    """

    def __init__(self, model_name: str, temperature: float, system_prompt: str, response_schema: Optional[content.Schema] = None, max_tokens: Optional[int] = 500):
        """Initialize a new BaseChatModel instance.

        Args:
            model_name (str): Name of the Gemini model to use
            temperature (float): Controls randomness in the model's responses. 
                Higher values (e.g., 0.8) make output more random, lower values (e.g., 0.2) make it more focused
            system_prompt (str): Initial system prompt to set model behavior and context
            response_schema (Optional[content.Schema]): Schema defining the expected response format.
                If provided, responses will be formatted as JSON matching this schema.
        """
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            top_p=0.95,
            top_k=40,
            max_output_tokens=max_tokens,
        )
        
        if response_schema:
            generation_config.response_schema = response_schema
            generation_config.response_mime_type = "application/json"
            
        self.model = genai.GenerativeModel(
            model_name,
            system_instruction=system_prompt,
            generation_config=generation_config
        )

        self._history: list[protos.Content] = []
    
    def _generate_response(self, prompt: str) -> str:
        """Generate a response from the model based on the given prompt.

        The prompt is added to the conversation history before generating the response.
        The response is also added to the history for context in future interactions.

        Args:
            prompt (str): The input text to send to the model

        Returns:
            str: The generated response text from the model

        Raises:
            GeminiModelError: If there is an error generating the response
        """

        logger = logging.getLogger(self.__class__.__module__)

        # Add prompt to history
        prompt_content = protos.Content(parts=[protos.Part(text=dedent(prompt))], role="user")
        self._history.append(prompt_content)
        
        try:    
            response = self.model.generate_content(self._history)
            self._history.append(response.candidates[0].content)
            return response.candidates[0].content.parts[0].text
        except Exception as e:
            # Roll back the prompt from history on error
            self._history.pop()
            logger.error(f"Error generating response: {e}")
            raise GeminiModelError(f"Error generating response: {e}") from e