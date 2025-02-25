"""
This test module demonstrates how to use structured output with the Gemini LLM.

Key concepts covered:
- Defining structured output schemas and parsing logic
- Creating system prompts to enforce response formats 
- Making LLM requests and handling structured responses
- Understanding rate limiting behavior and delays
"""

import json
from typing import Union

from bot.llm import (
    BaseStructuredOutput,
    ChatModelConfig,
    DeserializationError,
    GeminiChatModel,
    UnexpectedFinishReason,
    BaseResponseError
)
from bot.llm.gemini import response_content as content
from bot.types import LLMEngine


class MathProblemSolution(BaseStructuredOutput):
    solution: str

    @classmethod
    def llm_schema(cls, _engine: LLMEngine) -> content.Schema:
        return content.Schema(
            type=content.Type.OBJECT,
            enum=[],
            required=["answer"],
            properties={
                "answer": content.Schema(type=content.Type.STRING)
            }
        )

    @classmethod
    def deserialize(cls, json_str: str, _engine: LLMEngine) -> "MathProblemSolution":
        try:
            engine_output = json.loads(json_str)

            return MathProblemSolution(
                solution=engine_output["answer"]
            )

        except (json.JSONDecodeError, KeyError) as e:
            raise DeserializationError(
                f"Failed to parse Gemini response: {e}")


system_prompt = """
You are a math problem solver.

You will be provided with a number which is the result of a multiplication of two numbers.
You will need to return the one number that was multiplied by itself to get the result.

Example:
Input: 16
Output: 4

Input: 25
Output: 5

The output must follow the schema provided. Ensure that all fields are present and correctly formatted.
Schema Description:
- 'answer': The number that was multiplied by itself to get the result.
"""


class MathProblemSolver(GeminiChatModel):
    def __init__(self, model_name: str, request_limit: int, request_limit_period: int):
        model_config = ChatModelConfig(
            llm_model_name=model_name,
            temperature=0.2,
            max_tokens=8192,
            system_prompt=system_prompt,
            response_class=MathProblemSolution,
            request_limit=request_limit,
            request_limit_period_seconds=request_limit_period,
        )
        super().__init__(model_config)

    def solve(self, prompt: str) -> Union[MathProblemSolution, BaseResponseError]:
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

    # System prompt will be applied to all requests
    # as well as all responses will be deserialized into a MathProblemSolution

    solver = MathProblemSolver(
        model_name="gemini-2.0-flash", request_limit=2, request_limit_period=30)
    response = solver.solve("100")
    print(f"Square root of 100 is {response.solution}")

    response = solver.solve("9")
    print(f"Square root of 9 is {response.solution}")

    # This request will be delayed because of the rate limit
    response = solver.solve("81")
    print(f"Square root of 81 is {response.solution}")
