
from pydantic import BaseModel
from typing import Literal, List

class VocabularyItem(BaseModel):
    word: str
    translation: str

class NewsSummary(BaseModel):
    voice_tag: Literal['male', 'female']
    news_original: str
    news_translated: str
    vocabulary: List[VocabularyItem]