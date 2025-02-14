"""Configuration for Gemini agents."""

from dataclasses import dataclass

from ...settings import settings


@dataclass
class AgentConfig:
    """Configuration for a Gemini agent."""
    llm_model_name: str
    temperature: float
    max_tokens: int
    keep_raw_engine_responses: bool
    raw_engine_responses_dir: str
    request_limit: int
    request_limit_period_seconds: int


# Common configuration values
KEEP_RAW_RESPONSES = settings.keep_raw_engine_responses
RAW_RESPONSES_DIR = str(settings.raw_engine_responses_dir)

# Temperature values
CATEGORIZER_TEMPERATURE = 0.2
SUMMARIZER_TEMPERATURE = 1.0
VERIFIER_TEMPERATURE = 1.0
TRANSLATOR_TEMPERATURE = 0.2

# Max token values
CATEGORIZER_MAX_TOKENS = 8192
SUMMARIZER_MAX_TOKENS = 8192
VERIFIER_MAX_TOKENS = 8192
TRANSLATOR_MAX_TOKENS = 8192

# Model configurations
BASIC_MODEL = settings.agent_engine_basic_model
BASIC_MODEL_LIMIT = settings.agent_engine_basic_model_request_limit
BASIC_MODEL_LIMIT_PERIOD = settings.agent_engine_basic_model_request_limit_period_seconds

LIGHT_MODEL = settings.agent_engine_light_model
LIGHT_MODEL_LIMIT = settings.agent_engine_light_model_request_limit
LIGHT_MODEL_LIMIT_PERIOD = settings.agent_engine_light_model_request_limit_period_seconds

# Agent-specific configurations
categorizer = AgentConfig(
    llm_model_name=BASIC_MODEL,
    temperature=CATEGORIZER_TEMPERATURE,
    max_tokens=CATEGORIZER_MAX_TOKENS,
    keep_raw_engine_responses=KEEP_RAW_RESPONSES,
    raw_engine_responses_dir=RAW_RESPONSES_DIR,
    request_limit=BASIC_MODEL_LIMIT,
    request_limit_period_seconds=BASIC_MODEL_LIMIT_PERIOD
)

summarizer = AgentConfig(
    llm_model_name=LIGHT_MODEL,
    temperature=SUMMARIZER_TEMPERATURE,
    max_tokens=SUMMARIZER_MAX_TOKENS,
    keep_raw_engine_responses=KEEP_RAW_RESPONSES,
    raw_engine_responses_dir=RAW_RESPONSES_DIR,
    request_limit=LIGHT_MODEL_LIMIT,
    request_limit_period_seconds=LIGHT_MODEL_LIMIT_PERIOD
)

verifier = AgentConfig(
    llm_model_name=LIGHT_MODEL,
    temperature=VERIFIER_TEMPERATURE,
    max_tokens=VERIFIER_MAX_TOKENS,
    keep_raw_engine_responses=KEEP_RAW_RESPONSES,
    raw_engine_responses_dir=RAW_RESPONSES_DIR,
    request_limit=LIGHT_MODEL_LIMIT,
    request_limit_period_seconds=LIGHT_MODEL_LIMIT_PERIOD
)

translator = AgentConfig(
    llm_model_name=LIGHT_MODEL,
    temperature=TRANSLATOR_TEMPERATURE,
    max_tokens=TRANSLATOR_MAX_TOKENS,
    keep_raw_engine_responses=KEEP_RAW_RESPONSES,
    raw_engine_responses_dir=RAW_RESPONSES_DIR,
    request_limit=LIGHT_MODEL_LIMIT,
    request_limit_period_seconds=LIGHT_MODEL_LIMIT_PERIOD
) 