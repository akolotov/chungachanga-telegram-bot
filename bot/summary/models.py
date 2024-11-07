
from pydantic import BaseModel
from typing import Literal, List


class MinimalNewsSummary(BaseModel):
    voice_tag: Literal['male', 'female']
    news_original: str

class NewsContent(BaseModel):
    original_article: str
    summary: str

class AcronymItem(BaseModel):
    acronym: str
    full_form: str

class DeacronymizedItem(BaseModel):
    chain_of_thought: str
    acronyms: List[AcronymItem]
    summary: str

class EducatingVocabularyItem(BaseModel):
    word: str
    level: Literal['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
    importance: Literal['high', 'medium', 'low']
    translation_language: str
    translation: str
    synonyms_language: str
    synonyms: List[str]

class EducatingItem(BaseModel):
    chain_of_thought: str
    translated_summary: str
    vocabulary: List[EducatingVocabularyItem]

class VocabularyItem(BaseModel):
    word: str
    translation: str

class NewsSummary(MinimalNewsSummary):
    news_translated: str
    vocabulary: List[VocabularyItem]