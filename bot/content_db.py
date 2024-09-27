import json
import os
from typing import Dict, Optional, List
from pydantic import BaseModel

class VocabularyItem(BaseModel):
    word: str
    translation: str

class ContentDB:
    def __init__(self, db_file: str = "content_db.json") -> None:
        """
        Initialize the ContentDB with an optional database file.

        :param db_file: Path to the JSON file used for storing content data.
        """
        self.db_file = db_file
        self.db: Dict[str, Dict[str, any]] = self._load_db()

    def _load_db(self) -> Dict[str, Dict[str, any]]:
        """
        Load the content database from a JSON file.

        :return: A dictionary containing the content data.
        """
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_db(self) -> None:
        """
        Save the content database to a JSON file.
        """
        with open(self.db_file, 'w') as f:
            json.dump(self.db, f, indent=2)

    def add_content(self, url: str, content: Dict[str, str], vocabulary: Optional[List[VocabularyItem]] = None) -> None:
        """
        Add or update content for a given URL.

        :param url: The URL associated with the content.
        :param content: A dictionary containing the content data.
        :param vocabulary: An optional list of VocabularyItem objects representing the vocabulary.
        """
        self.db[url] = {**content, "vocabulary": [v.model_dump(mode='json') for v in vocabulary] if vocabulary else None}
        self._save_db()

    def get_content(self, url: str) -> Optional[Dict[str, any]]:
        """
        Retrieve content for a given URL.

        :param url: The URL associated with the content.
        :return: A dictionary containing the content data, or None if the URL does not exist.
        """
        content = self.db.get(url)
        if content:
            content = content.copy()  # Create a copy to avoid modifying the original
            if content.get("vocabulary"):
                content["vocabulary"] = [VocabularyItem(**item) for item in content["vocabulary"]]
        return content

    def url_exists(self, url: str) -> bool:
        """
        Check if a URL exists in the content database.

        :param url: The URL to check.
        :return: True if the URL exists, False otherwise.
        """
        return url in self.db

    def remove_content(self, url: str) -> None:
        """
        Remove content for a given URL.

        :param url: The URL associated with the content to be removed.
        """
        if url in self.db:
            del self.db[url]
            self._save_db()
