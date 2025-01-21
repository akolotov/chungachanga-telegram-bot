from bot.settings import settings

from .gemini import initialize as initialize_gemini
from .exceptions import ConfigurationError
from .types import LLMEngine

def initialize():
    if settings.agent_engine == LLMEngine.GEMINI:
        api_key = settings.agent_engine_api_key
        if not api_key:
            raise ConfigurationError(
                "Gemini API key not found. Please set the AGENT_ENGINE_API_KEY environment variable.")

        initialize_gemini(api_key=settings.agent_engine_api_key)
    else:
        pass
