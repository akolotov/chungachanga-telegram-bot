# Chat Models

This module provides wrappers around different LLM engines (Gemini, OpenAI, Ollama) for generating chat responses.

It is mostly focused on handling responses from LLM models to deserialize them into structured outputs.

It also automatically maintains the in-memory history of conversations by extending it with new prompts and responses.

Another feature that could be useful for debugging is the ability to save raw model responses to a file.

Since different LLM engines require different initialization procedures, an `initialize` function is provided to handle the initialization.

## Details

### Structured Outputs

If structured model responses are required, the corresponding response schema can be provided either during chat model initialization or as part of a particular generation request.

The schema is provided as a class that inherits from the `BaseStructuredOutput` class (defined in `bot/llm/types.py`).

The class should have a `llm_schema` class method that returns the schema definition for a particular LLM engine.

Another class method is `deserialize` that takes the raw model response and deserializes it into the corresponding class instance.

There are two main approaches to handling structured outputs:

#### A. Single Schema (Fixed Output Format)

Best suited when:

- The chat model performs a single, well-defined task
- All responses follow the same structure
- System prompt can fully define the expected output format
- Response processing is consistent across all inputs

Example implementation:

```python
class MathProblemSolution(BaseStructuredOutput):
    solution: str

    @classmethod
    def llm_schema(cls, _engine: LLMEngine) -> content.Schema:
        return content.Schema(
            type=content.Type.OBJECT,
            required=["solution"],
            properties={
                "solution": content.Schema(type=content.Type.STRING)
            }
        )
```

#### B. Multiple Schemas (Dynamic Output Format)

Preferred when:

- The chat model needs to handle different types of requests
- Different tasks require different response structures
- Each task needs its own specific prompt and schema
- Response processing varies based on the task type

Example implementation:

```python
class FirstAnalysis(BaseStructuredOutput):
    count: int
    items: List[str]

    @classmethod
    def llm_schema(cls, _engine: LLMEngine) -> content.Schema:
        return first_analysis_schema

class SecondAnalysis(BaseStructuredOutput):
    summary: str
    confidence: float

    @classmethod
    def llm_schema(cls, _engine: LLMEngine) -> content.Schema:
        return second_analysis_schema

# Usage in chat model:
response1 = chat_model.generate_response(prompt1, response_class=FirstAnalysis)
response2 = chat_model.generate_response(prompt2, response_class=SecondAnalysis)
```

### History

The in-memory history is automatically extended with new prompts and LLM responses.

If a prompt fails to generate a response, it is removed from the history.

### Raw Responses

If the `keep_raw_engine_responses` flag is set to `True`, the raw responses will be saved to a file.

The files are saved in the `raw_engine_responses` directory with the following structure:

```plaintext
raw_engine_responses/
    <session_id>/
        <agent_id>_<timestamp>.txt
```

where `session_id` is optional and, if provided, it is used to organize the files by session when several chats are being used in the same session.

The `agent_id` is used to distinguish responses from different chats within the same session.

### Implementation Details

#### Engine Initialization

Every wrapper provides an `initialize` method that is invoked based on the LLM engine name in the `bot/llm/initialize.py` file.

The main use case for the initialization is to set up the API key.

#### Rate Limiting

The chat models implement rate limiting to respect API quotas. Each model type (identified by `llm_model_name`) has its own rate limiter that:

- Tracks the number of requests made within a time window
- Automatically delays requests when the rate limit would be exceeded
- Maintains separate limits for different model types (e.g., different Gemini models)

Rate limits can be configured through `ChatModelConfig`:

- `request_limit`: Maximum number of requests allowed per time window
- `request_limit_period_seconds`: Time window in seconds for the request limit

When the rate limit is reached, the request is automatically delayed until the next time window, rather than failing.

#### Chat Initialization

The chat of a specific engine is operated by the chat model class.

The `__init__` method of the chat model class takes a `ChatModelConfig` (defined in `bot/llm/types.py`) instance as an argument and performs actions required to initialize the chat/completion/generation session with the specific LLM engine.

At this stage, the system prompt can be provided and the response schema can be set up to be used for all subsequent generation requests.

It also sets up an empty history for the chat.

To finish initialization with the common functionality for all engines, `__init__` of `BaseChatModel` (defined in `bot/llm/common.py`) is called.

#### Generation

If it is not redefined in the specific chat model, the `generate_response` method of the `BaseChatModel` is used.

If the response schema is provided with the generation request, it is added to the call to `_generate_response` method of the corresponding chat model.

The `_generate_response` method is responsible for extending the history with the new prompt and calling the corresponding method of the LLM engine with the parameters to generate the response with or without the structured output schema. It also handles error cases (and clears the history), calls `_save_response` of `BaseChatModel` to save the raw response to a file, and returns the result of generation compatible with the `BaseChatModelResponse` class (defined in `bot/llm/types.py`).

If the call to `_generate_response` is successful, `generate_response`, depending on whether the response schema is provided and if it is local for the particular prompt or for the model, calls the `_deserialize_response` method of the chat model to deserialize the structured response into the corresponding class instance. If no response schema is provided, the response is returned as is (as a string).

### Existing Chat Models Usage

The example below are for the Gemini chat model.

```python
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
            system_prompt=system_prompt,
            response_class=MathProblemSolution
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

    initialize()

    solver = MathProblemSolver(model_name="gemini-2.0-flash")
    response = solver.solve("100")
```

More examples can be found in the `bot/llm/gemini/tests` directory.

### Implementing New Chat Models

To add support for a new LLM engine:

1. Create a new module implementing the chat model:
   - Inherit from `BaseChatModel`
   - Implement `_generate_response(self, prompt: str, response_class: Optional[Any] = None) -> BaseChatModelResponse`
   - Implement `_deserialize_response(self, response: str, response_class: Any) -> BaseStructuredOutput`
   - Handle history management appropriately for the specific LLM engine

2. Add initialization support:
   - Create an `initialize()` function for the engine
   - Add the engine to the `LLMEngine` enum in `bot/llm/types.py`
   - Update the main `initialize()` function in `bot/llm/initialize.py`

### Error Handling

The chat models use two main types of responses:

- `RawChatModelResponse`: For unstructured text responses
- `DeserializedChatModelResponse`: For responses parsed into structured objects

Common errors that may occur (defined in `bot/llm/exceptions.py`):

- `GenerationError`: When the LLM fails to generate a response
- `UnexpectedFinishReason`: When the LLM stops generation for an unexpected reason

When errors occur, the prompt is automatically removed from history to maintain consistency.
