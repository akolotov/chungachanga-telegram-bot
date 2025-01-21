from typing import Dict, Optional, List, Any
from pydantic import BaseModel

from .base import BaseDB

class VocabularyItem(BaseModel):
    word: str
    translation: str

class ContentDB(BaseDB[Dict[str, Any]]):
    def __init__(self, db_file: str = "content_db.json") -> None:
        super().__init__(db_file)

    def add_content(self, url: str, content: Dict[str, str], vocabulary: Optional[List[VocabularyItem]] = None) -> None:
        """
        Add or update content for a given URL.

        :param url: The URL associated with the content.
        :param content: A dictionary containing the content data.
        :param vocabulary: An optional list of VocabularyItem objects representing the vocabulary.
        """
        def prepare(data: Dict[str, Any]) -> Dict[str, Any]:
            return {**data, "vocabulary": [v.model_dump(mode='json') for v in vocabulary] if vocabulary else None}
        
        super().add_content(url, content, prepare)

    def get_content(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve content for a given URL.

        :param url: The URL associated with the content.
        :return: A dictionary containing the content data, or None if the URL does not exist.
        """
        def parse(stored_content: Dict[str, Any]) -> Dict[str, Any]:
            content = stored_content.copy()
            if content.get("vocabulary"):
                content["vocabulary"] = [VocabularyItem(**item) for item in content["vocabulary"]]
            return content

        return super().get_content(url, parse)

    def url_exists(self, url: str) -> bool:
        """
        Check if a URL exists in the content database.

        :param url: The URL to check.
        :return: True if the URL exists, False otherwise.
        """
        return self.exists(url)
