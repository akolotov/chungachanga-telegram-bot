# Gemini-Powered News Processing Pipeline

A multi-agent system that processes Spanish news articles to create educational content for language learners. The system employs specialized agents powered by Google's Gemini API to generate concise summaries, expand acronyms, and provide educational support.

## Main Functionality

The pipeline processes news articles through three stages:

1. **Summarization**: Creates a B1-level Spanish summary optimized for ~20-second radio broadcasts
2. **Deacronymization**: Expands acronyms and abbreviations for better comprehension
3. **Educational Enhancement**: Adds translations and key vocabulary with CEFR levels

## Why Agents?

The agentic approach offers several advantages over a single large-prompt solution:

### 1. Focused Development and Debugging

- Each agent handles a specific task with clear inputs and outputs
- Prompts can be tuned and debugged independently
- Easier to identify and fix issues in specific processing stages

### 2. Model Efficiency

- Smaller, focused prompts are more reliable for instruction following
- Different models can be used for different tasks (e.g., more expensive models for critical tasks)
- Non-LLM solutions can be integrated where appropriate (e.g., vocabulary similarity checking)

### 3. Maintainability and Extensibility

- New agents can be added without affecting existing functionality
- Response validation can be implemented per agent
- Pipeline stages can be modified or reordered independently

### 4. Resource Optimization

- Rate limits can be managed per agent
- Token usage can be optimized for each specific task
- Processing can be distributed across different model tiers based on requirements

## Implementation Guide

### 1. Base Architecture

The system is built on a common base class that handles Gemini API interactions:

```python
class BaseChatModel:
    """Base class for Gemini model interactions with:
    - Configurable model settings
    - Response schema validation
    - Chat history tracking
    - Error handling
    """
```

### 2. Agent Pipeline

#### Summarizer Agent

```python
class Summarizer(BaseChatModel):
    """Creates B1-level Spanish summaries with:
    - 3-sentence limit
    - Voice tag assignment (male/female)
    - Cultural sensitivity checks
    """
```

#### Deacronymizer Agent

```python
class Deacronymizer(BaseChatModel):
    """Expands acronyms and abbreviations:
    - Identifies acronyms in Spanish text
    - Provides full forms
    - Maintains original language context
    """
```

#### Educator Agent

```python
class Educator(BaseChatModel):
    """Adds educational enhancements:
    - Translates content
    - Identifies key vocabulary
    - Assigns CEFR levels
    - Provides synonyms
    """
```

### 3. Pipeline Orchestration

The `summarize_article` function in `actor.py` orchestrates the pipeline:

```python
def summarize_article(article: str, session_id: str = "") -> Union[NewsSummary, ResponseError]:
    """
    1. Initializes agents with session tracking
    2. Processes article through each agent
    3. Handles errors and validation
    4. Returns final enhanced summary
    """
```

### 4. Response Validation

Each agent uses a defined schema for response validation:

- Ensures consistent output format
- Validates required fields
- Maintains data integrity through the pipeline

### 5. Error Handling

The system implements custom exceptions for different error types:

- `GeminiBaseError`: Base exception class
- `GeminiModelError`: Model interaction errors
- `GeminiUnexpectedFinishReason`: Unexpected response termination
- Agent-specific errors (e.g., `GeminiSummarizerError`)

## Constraints and Considerations

1. **Model Efficiency**
   - Each agent must operate within token limits
   - Responses must follow exact JSON formatting
   - Instructions must be clear and focused

2. **Rate Limiting**
   - API calls must respect Gemini's rate limits
   - Session tracking helps manage request distribution

3. **Response Quality**
   - Agents must validate and ensure quality of their specific tasks
   - Pipeline can be extended with additional validation agents

4. **Extensibility**
   - New agents can be added without disrupting existing pipeline
   - Different models can be used for different agents
   - Non-LLM solutions can be integrated where appropriate
