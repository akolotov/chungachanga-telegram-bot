from bot.llm import GeminiBaseError

class GeminiSummarizerError(GeminiBaseError):
    """Custom exception for Gemini Summarizer errors."""
    pass

class GeminiSummarizerVerificationError(GeminiBaseError):
    """Custom exception for Gemini Summarizer Verification errors."""
    pass

class GeminiTranslatorError(GeminiBaseError):
    """Custom exception for Gemini Translator errors."""
    pass

class GeminiCategorizerError(GeminiBaseError):
    """Custom exception for Gemini Categorizer errors."""
    pass
