class GenerationError(Exception):
    """Custom exception for generation errors."""
    pass

class UnexpectedFinishReason(GenerationError):
    """Custom exception for unexpected finish reasons."""
    pass

class DeserializationError(Exception):
    """Custom exception for deserialization errors."""
    pass

class ConfigurationError(Exception):
    """Custom exception for configuration errors."""
    pass
