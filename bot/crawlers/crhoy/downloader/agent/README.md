# Agent-Based News Processing Pipeline

This repository contains a standalone agent component that orchestrates news article analysis through a series of LLM-powered agents. The design is modular and extensible, leveraging the `bot.llm` module for consistent LLM interactions and centralized settings for configuration.

---

## Overview

The agent component processes news articles in a multi-stage pipeline using the `bot.llm` module's structured output capabilities and conversation management. The two primary responsibilities are:

- **Categorization:** Analyzes the article content to determine its category and, if necessary, generates a description for new or ambiguous categories.
- **Summarization:** Generates a concise summary of the news article, intended for quick consumption by a target audience. This stage may also incorporate translation capabilities via a dedicated translator agent.

---

## LLM Integration

All agents are built on top of the `bot.llm` module, which provides:

### Structured Outputs

Each agent defines its output schema using `BaseStructuredOutput`:

- `CategorizedArticle`: For categorization results
- `SummarizedArticle`: For article summaries
- `VerifiedSummary`: For verification results
- `TranslatedSummary`: For translations

Example from the Categorizer:

```python
class CategorizedArticle(BaseStructuredOutput):
    related: ArticleRelation
    category: str
    category_description: str

    @classmethod
    def llm_schema(cls, _engine: LLMEngine) -> content.Schema:
        return categorizer_structured_output
```

### Conversation Management

- Automatic maintenance of chat history
- Proper error handling and history cleanup
- Rate limiting for API requests

### Debug Capabilities

- Raw response storage for debugging
- Consistent logging across all agents
- Structured error handling

---

## Agent Components

### Categorizer Agent (`categorizer.py`)

- **Purpose:** Analyzes Spanish news articles to determine their relevance to Costa Rica and assigns appropriate categories
- **Features:**
  - Evaluates direct/indirect relation to Costa Rica
  - Matches content with existing categories
  - Suggests and describes new categories when needed
  - Uses structured output for consistent categorization  

### Summarizer Agent (`summarizer.py`)

- **Purpose:** Creates concise English summaries of Spanish news articles
- **Features:**
  - Analyzes article structure and key points
  - Generates summaries tailored for expats aged 25-45
  - Maintains casual, friendly tone while ensuring accuracy
  - Provides detailed news analysis including actors, actions, and consequences

### Summary Verifier Agent (`summary_verifier.py`)

- **Purpose:** Validates and improves English summaries
- **Features:**
  - Cross-checks summary against original article
  - Ensures factual accuracy and completeness
  - Suggests adjustments when needed
  - Maintains consistent style guidelines

### Translator Agent (`translator.py`)

- **Purpose:** Translates English summaries to other languages (e.g., Russian)
- **Features:**
  - Preserves meaning and tone
  - Adapts content for target language audience
  - Maintains clarity and accessibility

---

## Environment Configuration

The functionality of the agents is driven by configuration defined in `agents_config.py`, which sources its values from `settings.py`. Key parameters include:

### Model Configurations

- **Basic Model (`BASIC_MODEL`):**
  - Used for sophisticated tasks requiring advanced reasoning (e.g., categorization)
  - Handles tasks needing real-world knowledge and complex analysis
  - Configurable request limits and time windows

- **Light Model (`LIGHT_MODEL`):**
  - Used for straightforward tasks (summarization, translation, verification)
  - Optimized for tasks with well-defined patterns and structures
  - Separate request limits and time windows

### Agent-Specific Settings

Each agent has its own `AgentConfig` instance with:

- Temperature settings (controlling response creativity)
- Maximum token limits
- Response storage configuration for debugging purposes
- Request rate limiting

---

## Prompt System

The `prompts` directory contains structured templates for each agent:

- `category.py`: Defines categorization guidelines and output schema
- `summary.py`: Specifies summarization rules and analysis structure
- `verification.py`: Details verification criteria and adjustment format
- `translation.py`: Outlines translation requirements and output format

Each prompt file includes:

- System instructions for the LLM
- Structured output schema definition

---

## Implementing a New Agent

1. **Define Structured Output:**
   There are two approaches to handling structured outputs:

   A. Single Schema (Fixed Output Format):
   Best suited when:
   - The agent performs a single, well-defined task
   - All responses follow the same structure
   - System prompt can fully define the expected output format
   - Response processing is consistent across all inputs
   Example use case: The Categorizer agent, which always returns category, relation, and description.

   ```python
   class NewAgentOutput(BaseStructuredOutput):
       field1: str
       field2: int

       @classmethod
       def llm_schema(cls, _engine: LLMEngine) -> content.Schema:
           return content.Schema(
               type=content.Type.OBJECT,
               required=["field1", "field2"],
               properties={
                   "field1": content.Schema(type=content.Type.STRING),
                   "field2": content.Schema(type=content.Type.INTEGER)
               }
           )
   ```

   B. Multiple Schemas (Dynamic Output Format):
   Preferred when:
   - The agent needs to handle different types of requests
   - Different tasks require different response structures
   - Each task needs its own specific prompt and schema
   - Response processing varies based on the task
   - A text or corpus of documents is provided in the system prompt, and different requests analyze this input in different ways

   Example use cases:
   - An analysis agent that can both count items and list their properties
   - A document analyzer that can extract different types of information (statistics, names, dates) from the same text

   ```python
   class FirstOutput(BaseStructuredOutput):
       field1: str

       @classmethod
       def llm_schema(cls, _engine: LLMEngine) -> content.Schema:
           return first_output_schema

   class SecondOutput(BaseStructuredOutput):
       field2: int

       @classmethod
       def llm_schema(cls, _engine: LLMEngine) -> content.Schema:
           return second_output_schema
   ```

2. **Create Agent Configuration:**
   - Add a new `AgentConfig` instance in `agents_config.py`
   - Choose appropriate model (basic/light) based on task complexity
   - Configure temperature, tokens, and rate limits
   - Add any new configuration parameters to `settings.py`

3. **Implement Agent Class:**
   Choose implementation based on your schema approach:

   A. Single Schema:

   ```python
   class NewAgent(GeminiChatModel):
       def __init__(self, session_id: str = ""):
           config = agents_config.new_agent
           model_config = ChatModelConfig(
               session_id=session_id,
               agent_id="new_agent",
               llm_model_name=config.llm_model_name,
               temperature=config.temperature,
               system_prompt=new_agent_prompt,
               response_class=NewAgentOutput,  # Fixed schema
               # ... other config
           )
           super().__init__(model_config)

       def process(self, input: str) -> Union[NewAgentOutput, BaseResponseError]:
           try:
               model_response = self.generate_response(input)
           except UnexpectedFinishReason as e:
               return BaseResponseError(error=f"LLM engine responded with: {e}")
           return model_response.response
   ```

   B. Multiple Schemas:

   ```python
   class NewAgent(GeminiChatModel):
       def __init__(self, session_id: str = ""):
           config = agents_config.new_agent
           model_config = ChatModelConfig(
               session_id=session_id,
               agent_id="new_agent",
               llm_model_name=config.llm_model_name,
               temperature=config.temperature,
               system_prompt=base_prompt,  # Basic instructions only
               # No fixed response_class
               # ... other config
           )
           super().__init__(model_config)

       def process_first(self, input: str) -> Union[FirstOutput, BaseResponseError]:
           try:
               model_response = self.generate_response(
                   prompt=first_prompt + input,
                   response_class=FirstOutput
               )
           except UnexpectedFinishReason as e:
               return BaseResponseError(error=f"LLM engine responded with: {e}")
           return model_response.response

       def process_second(self, input: str) -> Union[SecondOutput, BaseResponseError]:
           try:
               model_response = self.generate_response(
                   prompt=second_prompt + input,
                   response_class=SecondOutput
               )
           except UnexpectedFinishReason as e:
               return BaseResponseError(error=f"LLM engine responded with: {e}")
           return model_response.response
   ```

4. **Implement Pipeline Integration:**
   - Create orchestration functions in `actor.py` if the agent is part of a pipeline
   - Handle agent output transformation if needed
   - Example:

   ```python
   def process_with_new_agent(input: str, session_id: str = "") -> Union[ProcessedOutput, BaseResponseError]:
       try:
           agent = NewAgent(session_id)
           result = agent.process(input)
           if isinstance(result, BaseResponseError):
               return result
           
           # Transform output if needed
           return ProcessedOutput(
               field1=result.field1,
               field2=result.field2
           )
       except NewAgentError as e:
           logger.error(f"Unexpected error: {str(e)}")
           raise NewAgentError(f"Processing failed: {str(e)}")
   ```
