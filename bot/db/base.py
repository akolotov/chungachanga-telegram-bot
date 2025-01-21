import json
import os
from typing import Dict, Optional, TypeVar, Generic, Callable, Any

T = TypeVar('T')

class BaseDB(Generic[T]):
    def __init__(self, db_file: str) -> None:
        """
        Initialize the BaseDB with a database file.

        :param db_file: Path to the JSON file used for storing data.
        """
        self.db_file = db_file
        self.db: Dict[str, Any] = self._load_db()

    def _load_db(self) -> Dict[str, Any]:
        """
        Load the database from a JSON file.

        :return: A dictionary containing the data.
        """
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_db(self) -> None:
        """
        Save the database to a JSON file.
        """
        with open(self.db_file, 'w') as f:
            json.dump(self.db, f, indent=2)

    def add_content(self, key: str, content: T, prepare_callback: Callable[[T], Any]) -> None:
        """
        Add or update content for a given key.

        :param key: The key associated with the content.
        :param content: The content data.
        :param prepare_callback: Callback function to prepare the content for storage.
        """
        self.db[key] = prepare_callback(content)
        self._save_db()

    def get_content(self, key: str, parse_callback: Callable[[Any], T]) -> Optional[T]:
        """
        Retrieve content for a given key.

        :param key: The key associated with the content.
        :param parse_callback: Callback function to parse the stored content.
        :return: The content data, or None if the key does not exist.
        """
        content = self.db.get(key)
        if content is not None:
            return parse_callback(content)
        return None

    def exists(self, key: str) -> bool:
        """
        Check if a key exists in the database.

        :param key: The key to check.
        :return: True if the key exists, False otherwise.
        """
        return key in self.db

    def remove_content(self, key: str) -> None:
        """
        Remove content for a given key.

        :param key: The key associated with the content to be removed.
        """
        if key in self.db:
            del self.db[key]
            self._save_db()
