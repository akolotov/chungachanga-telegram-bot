"""Configuration for Gemini agents."""

from dataclasses import dataclass
from typing import Optional

from ...settings import settings
from bot.llm import SupportModelConfig


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
    supplementary_model_config: Optional[SupportModelConfig] = None


# Common configuration values
KEEP_RAW_RESPONSES = settings.keep_raw_engine_responses
RAW_RESPONSES_DIR = str(settings.raw_engine_responses_dir)

# Temperature values
CLASSIFIER_TEMPERATURE = 0.2
LABELER_TEMPERATURE = 0.2
NAMER_TEMPERATURE = 0.2
SUMMARIZER_TEMPERATURE = 1.0
TRANSLATOR_TEMPERATURE = 0.2

# Max token values
CLASSIFIER_MAX_TOKENS = 16384
LABELER_MAX_TOKENS = 8192
NAMER_MAX_TOKENS = 8192
SUMMARIZER_MAX_TOKENS = 16384
TRANSLATOR_MAX_TOKENS = 8192

# Model configurations
BASIC_MODEL = settings.agent_engine_basic_model
BASIC_MODEL_LIMIT = settings.agent_engine_basic_model_request_limit
BASIC_MODEL_LIMIT_PERIOD = settings.agent_engine_basic_model_request_limit_period_seconds
BASIC_MODEL_REQUIRES_SUPPLEMENTARY = settings.agent_engine_basic_model_requires_supplementary

LIGHT_MODEL = settings.agent_engine_light_model
LIGHT_MODEL_LIMIT = settings.agent_engine_light_model_request_limit
LIGHT_MODEL_LIMIT_PERIOD = settings.agent_engine_light_model_request_limit_period_seconds
LIGHT_MODEL_REQUIRES_SUPPLEMENTARY = settings.agent_engine_light_model_requires_supplementary

SUPPLEMENTARY_MODEL = settings.agent_engine_supplementary_model
SUPPLEMENTARY_MODEL_LIMIT = settings.agent_engine_supplementary_model_request_limit
SUPPLEMENTARY_MODEL_LIMIT_PERIOD = settings.agent_engine_supplementary_model_request_limit_period_seconds
SUPPLEMENTARY_MODEL_TEMPERATURE = 0.0

# Agent-specific configurations
classifier = AgentConfig(
    llm_model_name=BASIC_MODEL,
    temperature=CLASSIFIER_TEMPERATURE,
    max_tokens=CLASSIFIER_MAX_TOKENS,
    keep_raw_engine_responses=KEEP_RAW_RESPONSES,
    raw_engine_responses_dir=RAW_RESPONSES_DIR,
    request_limit=BASIC_MODEL_LIMIT,
    request_limit_period_seconds=BASIC_MODEL_LIMIT_PERIOD,
    supplementary_model_config=SupportModelConfig(
        llm_model_name=SUPPLEMENTARY_MODEL,
        temperature=SUPPLEMENTARY_MODEL_TEMPERATURE,
        request_limit=SUPPLEMENTARY_MODEL_LIMIT,
        request_limit_period_seconds=SUPPLEMENTARY_MODEL_LIMIT_PERIOD
    ) if BASIC_MODEL_REQUIRES_SUPPLEMENTARY else None
)

labeler = AgentConfig(
    llm_model_name=BASIC_MODEL,
    temperature=LABELER_TEMPERATURE,
    max_tokens=LABELER_MAX_TOKENS,
    keep_raw_engine_responses=KEEP_RAW_RESPONSES,
    raw_engine_responses_dir=RAW_RESPONSES_DIR,
    request_limit=BASIC_MODEL_LIMIT,
    request_limit_period_seconds=BASIC_MODEL_LIMIT_PERIOD,
    supplementary_model_config=SupportModelConfig(
        llm_model_name=SUPPLEMENTARY_MODEL,
        temperature=SUPPLEMENTARY_MODEL_TEMPERATURE,
        request_limit=SUPPLEMENTARY_MODEL_LIMIT,
        request_limit_period_seconds=SUPPLEMENTARY_MODEL_LIMIT_PERIOD
    ) if BASIC_MODEL_REQUIRES_SUPPLEMENTARY else None
)

namer = AgentConfig(
    llm_model_name=LIGHT_MODEL,
    temperature=NAMER_TEMPERATURE,
    max_tokens=NAMER_MAX_TOKENS,
    keep_raw_engine_responses=KEEP_RAW_RESPONSES,
    raw_engine_responses_dir=RAW_RESPONSES_DIR,
    request_limit=LIGHT_MODEL_LIMIT,
    request_limit_period_seconds=LIGHT_MODEL_LIMIT_PERIOD
)

label_finalizer = AgentConfig(
    llm_model_name=BASIC_MODEL,
    temperature=LABELER_TEMPERATURE,
    max_tokens=LABELER_MAX_TOKENS,
    keep_raw_engine_responses=KEEP_RAW_RESPONSES,
    raw_engine_responses_dir=RAW_RESPONSES_DIR,
    request_limit=BASIC_MODEL_LIMIT,
    request_limit_period_seconds=BASIC_MODEL_LIMIT_PERIOD,
    supplementary_model_config=SupportModelConfig(
        llm_model_name=SUPPLEMENTARY_MODEL,
        temperature=SUPPLEMENTARY_MODEL_TEMPERATURE,
        request_limit=SUPPLEMENTARY_MODEL_LIMIT,
        request_limit_period_seconds=SUPPLEMENTARY_MODEL_LIMIT_PERIOD
    ) if BASIC_MODEL_REQUIRES_SUPPLEMENTARY else None
)

summarizer = AgentConfig(
    llm_model_name=BASIC_MODEL,
    temperature=SUMMARIZER_TEMPERATURE,
    max_tokens=SUMMARIZER_MAX_TOKENS,
    keep_raw_engine_responses=KEEP_RAW_RESPONSES,
    raw_engine_responses_dir=RAW_RESPONSES_DIR,
    request_limit=BASIC_MODEL_LIMIT,
    request_limit_period_seconds=BASIC_MODEL_LIMIT_PERIOD,
    supplementary_model_config=SupportModelConfig(
        llm_model_name=SUPPLEMENTARY_MODEL,
        temperature=SUPPLEMENTARY_MODEL_TEMPERATURE,
        request_limit=SUPPLEMENTARY_MODEL_LIMIT,
        request_limit_period_seconds=SUPPLEMENTARY_MODEL_LIMIT_PERIOD
    ) if BASIC_MODEL_REQUIRES_SUPPLEMENTARY else None
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