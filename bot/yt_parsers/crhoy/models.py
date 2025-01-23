from typing import List, Union

from pydantic import BaseModel

class TranscriptionWord(BaseModel):
    word: str
    start: float
    end: float

class NewsStory(BaseModel):
    id: str
    text: str
    start: Union[float, None]
    end: Union[float, None]
    start_similarity: float
    end_similarity: float

class CapturedNewsStory(BaseModel):
    id: str
    text: str
    audio: str
    url: str

class TranscriptionData(BaseModel):
    text: str
    words: List[TranscriptionWord]

class TranscribedSequences(BaseModel):
    intro: str
    stories: List[str]
    outro: str 