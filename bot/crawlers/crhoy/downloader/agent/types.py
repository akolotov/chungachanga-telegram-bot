from enum import Enum
from pydantic import BaseModel

class ArticleRelation(str, Enum):
    """Enum for article's relation to Costa Rica."""
    DIRECTLY = "directly"
    INDIRECTLY = "indirectly"
    NOT_APPLICABLE = "na"

class ActorWorkItem(BaseModel):
    """Data structure for passing article content between agents."""
    original_article: str
    summary: str

class ArticleSummary(BaseModel):
    """Data structure for the final article summary."""
    summary: str
    translated_summary: str

class ArticleCategory(BaseModel):
    """Data structure for article categorization results."""
    related: ArticleRelation
    category: str
    category_description: str 