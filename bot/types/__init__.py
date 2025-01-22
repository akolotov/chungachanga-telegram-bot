from enum import Enum

# Enum for the LLM engines
class LLMEngine(Enum):
    GEMINI = "gemini"
    OPENAI = "openai"
    OLLAMA = "ollama"

__all__ = ["LLMEngine"]