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
