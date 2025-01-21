from bot.llm import GeminiBaseError

class GeminiSummarizerError(GeminiBaseError):
    """Custom exception for Gemini Summarizer errors."""
    pass

class GeminiSummarizerVerificationError(GeminiBaseError):
    """Custom exception for Gemini Summarizer Verification errors."""
    pass

class GeminiDeacronymizerError(GeminiBaseError):
    """Custom exception for Gemini Deacronymizer errors."""
    pass

class GeminiEducatorError(GeminiBaseError):
    """Custom exception for Gemini Educator errors."""
    pass
