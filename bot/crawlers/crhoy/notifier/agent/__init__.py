"""Gemini-powered agents for processing Spanish news articles."""

from .types import (
    ArticleRelation,
    ArticleSummary,
    ArticleCategory
)

from .actor import (
    categorize_article,
    summarize_article
)

__all__ = [
    # Types
    "ArticleRelation",
    "ArticleSummary",
    "ArticleCategory",
    
    # Functions
    "categorize_article",
    "summarize_article"
] 