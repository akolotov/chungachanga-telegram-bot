"""
This test module demonstrates ability to use a Gemini's thinking model.

Contains demonstrations for:
- Using a thinking model to generate a response
- Using a supplementary model to represent the thinking model's response as
  a structured output
- Keeping raw engine responses for analysis and debugging
"""

import json
from typing import Union

from bot.llm import (
    BaseStructuredOutput,
    ChatModelConfig,
    SupportModelConfig,
    DeserializationError,
    GeminiChatModel,
    UnexpectedFinishReason,
    BaseResponseError
)
from bot.llm.gemini import response_content as content
from bot.types import LLMEngine

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
    
class MathProblemSolution(BaseStructuredOutput):
    solution: str

    @classmethod
    def llm_schema(cls, _engine: LLMEngine) -> content.Schema:
        return content.Schema(
            type=content.Type.OBJECT,
            enum=[],
            required=["a_chain_of_thought", "b_answer"],
            properties={
                "a_chain_of_thought": content.Schema(
                    type=content.Type.STRING,
                ),
                "b_answer": content.Schema(type=content.Type.STRING)
            }
        )

    @classmethod
    def deserialize(cls, json_str: str, _engine: LLMEngine) -> "MathProblemSolution":
        try:
            engine_output = json.loads(json_str)

            return MathProblemSolution(
                solution=engine_output["b_answer"]
            )

        except (json.JSONDecodeError, KeyError) as e:
            raise DeserializationError(
                f"Failed to parse Gemini response: {e}")


system_prompt = """
You are a math problem solver.

You will be provided with a number which is the result of a multiplication of two numbers.
You will need to return the one number that was multiplied by itself to get the result.

## Output format

- Provide JSON output following the specified schema.
- Ensure all fields are present and correctly formatted.
- DON'T ADD any introductory text or comments before the JSON; adherence is mandatory to avoid penalties.

Schema Description:
- 'a_chain_of_thought': A detailed, step-by-step chain of thought process for the answer.
  The process must include either all or at least two of the following:
  - verification ("Let me check my answer ..."),
  - subgoal setting ("Let me break down the problem into smaller steps ..."),
  - backtracking ("Let's try a different approach, what if ...?"),
  - backward chaining ("Let me use the answer to check my work ...").
- 'b_answer': The number that was multiplied by itself to get the result.

## Examples
Example #1:
User prompt: 16
Output:
{"a_chain_of_thought":"Reasoning to conclude the answer","b_answer":"4"}

Example #2:
User prompt: 25
Output:
{"a_chain_of_thought":"Reasoning to conclude the answer","b_answer":"5"}
"""


class MathProblemSolver(GeminiChatModel):
    def __init__(self, model_name: str, support_model_name: str):
        support_model_config = SupportModelConfig(
            llm_model_name=support_model_name,
            temperature=0.0
        )

        model_config = ChatModelConfig(
            llm_model_name=model_name,
            temperature=0.2,
            max_tokens=1024*8,
            system_prompt=system_prompt,
            response_class=MathProblemSolution,
            support_model_config=support_model_config,
            session_id="test",
            agent_id="gemini.thinking",
            keep_raw_engine_responses=True,
            raw_engine_responses_dir="data/responses"
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

    print("Receive a simple response by using the thinking model")
    print("----------------------------------------------------")
    basic_model = BasicChat(model_name="gemini-2.0-flash-thinking-exp-01-21")
    response = basic_model.generate(
        "Let's do it simple: 4 x 4 = 16, 3 x 3 = 9. What number in the left part if the right is 100?")
    print(response)
    print()

    print("Receive a structured response by using the thinking model")
    print("--------------------------------------------------------")
    # Use a supplementary model together with the thinking model to deserialize
    # the response into a MathProblemSolution object
    solver = MathProblemSolver(
        model_name="gemini-2.0-flash-thinking-exp-01-21",
        support_model_name="gemini-2.0-flash-lite"
    )
    response = solver.solve("100")
    print(f"Square root of 100 is {response.solution}")
