class GeminiModelError(Exception):
    """Custom exception for Gemini Model errors."""
    pass

class GeminiUnexpectedFinishReason(Exception):
    """Custom exception for unexpected finish reasons."""
    pass

class GeminiBaseError(Exception):
    """Custom exception for Gemini errors."""
    pass

class GeminiSummarizerError(GeminiBaseError):
    """Custom exception for Gemini Summarizer errors."""
    pass

class GeminiDeacronymizerError(GeminiBaseError):
    """Custom exception for Gemini Deacronymizer errors."""
    pass

class GeminiEducatorError(GeminiBaseError):
    """Custom exception for Gemini Educator errors."""
    pass
