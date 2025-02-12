
from pydantic import BaseModel
from typing import Literal, List

from bot.llm import BaseResponseError

class ResponseError(BaseResponseError):
    pass

class NewsContent(BaseModel):
    original_article: str
    summary: str

class EducatingVocabularyItem(BaseModel):
    word: str
    level: Literal['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
    importance: Literal['high', 'medium', 'low']
    translation_language: str
    translation: str
    synonyms_language: str
    synonyms: List[str]

class VocabularyItem(BaseModel):
    word: str
    translation: str

class NewsSummary(BaseModel):
    voice_tag: Literal['male', 'female']
    news_original: str
    news_translated: str
    vocabulary: List[VocabularyItem]