"""
This test module demonstrates basic chat functionality with the Gemini LLM.

Contains demonstrations for:
- Both simple and multi-turn conversation
- System prompt enforcement
"""

from typing import Union

from bot.llm import (
    ChatModelConfig,
    GeminiChatModel,
    UnexpectedFinishReason,
    BaseResponseError
)


class BasicChat(GeminiChatModel):
    def __init__(self, model_name: str):
        model_config = ChatModelConfig(
            llm_model_name=model_name,
            temperature=0.2,
            max_tokens=8192,
        )
        super().__init__(model_config)

    def generate(self, prompt: str) -> Union[str, BaseResponseError]:
        try:
            model_response = self.generate_response(prompt)
        except UnexpectedFinishReason as e:
            return BaseResponseError(error=f"LLM engine responded with: {e}")
        except Exception:
            raise

        return model_response.response


class BasicChatWithSystemPrompt(GeminiChatModel):
    def __init__(self, model_name: str, system_prompt: str):
        model_config = ChatModelConfig(
            llm_model_name=model_name,
            temperature=1.0,
            max_tokens=8192,
            system_prompt=system_prompt
        )
        super().__init__(model_config)

    def generate(self, prompt: str) -> Union[str, BaseResponseError]:
        try:
            model_response = self.generate_response(prompt)
        except UnexpectedFinishReason as e:
            return BaseResponseError(error=f"LLM engine responded with: {e}")
        except Exception:
            raise

        return model_response.response


if __name__ == "__main__":
    from bot.llm import initialize

    # Assumes that the module bot.settings is available
    # and `AGENT_ENGINE_API_KEY` is set in the environment variables
    initialize()

    # Receive a simple response
    basic_model = BasicChat(model_name="gemini-2.0-flash")
    response = basic_model.generate(
        "Let's do it simple: 4 x 4 = 16, 3 x 3 = 9. What number in the left part if the right is 100?")
    print(response)

    # Expect a response in Spanish since the system prompt is set
    system_prompt_model = BasicChatWithSystemPrompt(
        model_name="gemini-2.0-flash", system_prompt="Always respond in Spanish.")
    response = system_prompt_model.generate("Hello, how are you?")
    print(response)

    # Expect a response that takes into account the history of the conversation
    response = basic_model.generate(
        "What number in the left part if the right is 25?")
    print(response)
