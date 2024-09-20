import json
import os
from typing import Dict, Optional, List
from pydantic import BaseModel

class VocabularyItem(BaseModel):
    word: str
    translation: str

class ContentDB:
    def __init__(self, db_file: str = "content_db.json"):
        self.db_file = db_file
        self.db: Dict[str, Dict[str, any]] = self._load_db()

    def _load_db(self) -> Dict[str, Dict[str, any]]:
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_db(self):
        with open(self.db_file, 'w') as f:
            json.dump(self.db, f, indent=2)

    def add_content(self, url: str, content: Dict[str, str], vocabulary: Optional[List[VocabularyItem]] = None):
        self.db[url] = {**content, "vocabulary": [v.model_dump(mode = 'json') for v in vocabulary] if vocabulary else None}
        self._save_db()

    def get_content(self, url: str) -> Optional[Dict[str, any]]:
        content = self.db.get(url)
        if content:
            content = content.copy()  # Create a copy to avoid modifying the original
            if content.get("vocabulary"):
                content["vocabulary"] = [VocabularyItem(**item) for item in content["vocabulary"]]
        return content

    def url_exists(self, url: str) -> bool:
        return url in self.db

    def remove_content(self, url: str):
        if url in self.db:
            del self.db[url]
            self._save_db()