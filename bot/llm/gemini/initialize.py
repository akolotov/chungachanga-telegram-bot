import google.generativeai as genai

# Singleton to track initialization status
_initialized = False

def initialize(api_key: str):
    global _initialized
    genai.configure(api_key=api_key)
    _initialized = True

def is_initialized() -> bool:
    return _initialized

