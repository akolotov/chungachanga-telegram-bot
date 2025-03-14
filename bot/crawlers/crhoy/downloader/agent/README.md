# Agent-Based News Processing Pipeline

This repository contains a standalone agent component that orchestrates news article analysis through a series of LLM-powered agents. The design is modular and extensible, leveraging the `bot.llm` module for consistent LLM interactions and centralized settings for configuration.

---

## Overview

The agent component processes news articles in a multi-stage pipeline using the `bot.llm` module's structured output capabilities and conversation management. The two primary responsibilities are:

- **Categorization:** Analyzes the article content to determine its category through a multi-agent pipeline that classifies, labels, names, and finalizes categories.
- **Summarization:** Generates a concise summary of the news article, intended for quick consumption by a target audience. This stage may also incorporate translation capabilities via a dedicated translator agent.

---

## LLM Integration

All agents are built on top of the `bot.llm` module, which provides:

### Structured Outputs

Each agent defines its output schema using `BaseStructuredOutput`:

- `ClassifiedArticle`: For article relation classification
- `LabeledArticle`: For category labeling results
- `NamedCategory`: For new category naming
- `FinalizedLabel`: For category finalization
- `SummarizedArticle`: For article summaries
- `TranslatedSummary`: For translations

Example from the Labeler, which handles more complex structured output:

```python
@dataclass
class CategorySuggestion:
    """Represents a category suggestion with its suitability rank."""
    category: str
    rank: int

class LabeledArticle(BaseStructuredOutput):
    """Structured output for article labeling."""
    no_category: bool
    suggested_categories: List[CategorySuggestion]

    @classmethod
    def llm_schema(cls, _engine: LLMEngine) -> content.Schema:
        return labeler_structured_output
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

### Classifier Agent (`classifier.py`)

- **Purpose:** Determines whether a Spanish news article is related to Costa Rica
- **Features:**
  - Evaluates if the article is directly related, indirectly related, or not related to Costa Rica
  - Uses structured output to provide consistent classification
  - Returns an ArticleRelation enum value (DIRECTLY, INDIRECTLY, NOT_APPLICABLE)

### Labeler Agent (`labeler.py`)

- **Purpose:** Identifies potential existing categories that match the article content
- **Features:**
  - Analyzes article content against existing category definitions
  - Ranks categories by relevance to the article
  - Determines if no existing category is suitable
  - Returns a list of CategorySuggestion objects with ranks

### Namer Agent (`namer.py`)

- **Purpose:** Suggests new category names and descriptions when existing categories don't fit
- **Features:**
  - Creates concise, descriptive category names
  - Generates comprehensive category descriptions
  - Ensures consistency with existing category naming conventions
  - Returns a NamedCategory with name and description

### Label Finalizer Agent (`label_finalizer.py`)

- **Purpose:** Makes the final decision between existing and new categories
- **Features:**
  - Compares suitability of existing categories against newly suggested ones
  - Uses obfuscation techniques to prevent bias toward new or existing categories
  - Makes a definitive category selection
  - Returns a FinalizedLabel with the chosen category

### Summarizer Agent (`summarizer.py`)

- **Purpose:** Creates concise English summaries of Spanish news articles
- **Features:**
  - Analyzes article structure and key points
  - Generates summaries tailored for expats aged 25-45
  - Maintains casual, friendly tone while ensuring accuracy
  - Provides detailed news analysis including actors, actions, and consequences

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
  - Used for sophisticated tasks requiring advanced reasoning (e.g., classification, labeling)
  - Handles tasks needing real-world knowledge and complex analysis
  - Configurable request limits and time windows
  - May require a supplementary model for structured output processing

- **Light Model (`LIGHT_MODEL`):**
  - Used for straightforward tasks (summarization, translation)
  - Optimized for tasks with well-defined patterns and structures
  - Separate request limits and time windows
  - Generally doesn't require supplementary model assistance

- **Supplementary Model (`SUPPLEMENTARY_MODEL`):**
  - Assists the primary models with structured output processing
  - Used when the primary model has limitations with structured output functionality
  - Runs with minimal temperature (0.0) for deterministic parsing
  - Has its own request limits and time windows
  - Configured via `SupportModelConfig` in agent configurations

Example supplementary model configuration:

```python
supplementary_model_config=SupportModelConfig(
    llm_model_name=SUPPLEMENTARY_MODEL,
    temperature=SUPPLEMENTARY_MODEL_TEMPERATURE,
    request_limit=SUPPLEMENTARY_MODEL_LIMIT,
    request_limit_period_seconds=SUPPLEMENTARY_MODEL_LIMIT_PERIOD
) if BASIC_MODEL_REQUIRES_SUPPLEMENTARY else None
```

### Agent-Specific Settings

Each agent has its own `AgentConfig` instance with:

- Temperature settings (controlling response creativity)
- Maximum token limits
- Response storage configuration for debugging purposes
- Request rate limiting
- Supplementary model configuration (if required)

---

## Prompt System

The `prompts` directory contains structured templates for each agent:

- `relation.py`: Defines classification guidelines for article relation to Costa Rica
- `label.py`: Specifies labeling rules for matching articles to existing categories
- `new_label.py`: Outlines requirements for creating new category names and descriptions
- `label_finalization.py`: Details criteria for finalizing category selection
- `summary.py`: Specifies summarization rules and analysis structure
- `translation.py`: Outlines translation requirements and output format

Each prompt file includes:

- System instructions for the LLM
- Structured output schema definition

---

## Orchestration

The `actor.py` file provides high-level functions that orchestrate the multi-agent pipeline:

- `categorize_article()`: Coordinates the four-stage categorization process:
  1. Classification with Classifier
  2. Labeling with Labeler
  3. Naming with Namer (if needed)
  4. Finalization with LabelFinalizer

- `summarize_article()`: Manages the summarization and translation process:
  1. Summarization with Summarizer
  2. Translation with Translator (if needed)

These functions handle the flow of information between agents, error handling, and returning the final results.

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
   Example use case: The Classifier agent, which always returns an ArticleRelation value.

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
   - Determine if a supplementary model is needed for structured output processing

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
