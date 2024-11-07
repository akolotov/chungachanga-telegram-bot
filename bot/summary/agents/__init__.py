from .gemini.actor import summarize_article as summarize_article_by_gemini
from .openai.actor import summarize_article as summarize_article_by_openai

__all__ = ['summarize_article_by_gemini', 'summarize_article_by_openai']
