import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Class responsible for loading and accessing application configuration.
class AppConfig:
    def __init__(self):
        self.path = Path("filter_keywords.json")

        if not self.path.exists():
            self.path = Path("filter_keywords_example.json")

        logger.info(f"Loading config: {self.path}")

        self._data = self._load()

    # Loads configuration data from a JSON file.
    def _load(self):
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    # Returns a list of values from configuration using nested keys.
    def get_list(self, keys: list[str]) -> list:
        current = self._data

        for key in keys:
            if not isinstance(current, dict):
                return []
            current = current.get(key, {})

        return current if isinstance(current, list) else []

    # Returns a dictionary from configuration using nested keys.
    def get_dict(self, keys: list[str]) -> dict:
        current = self._data

        for key in keys:
            if not isinstance(current, dict):
                return {}
            current = current.get(key, {})

        return current if isinstance(current, dict) else {}


# Creates a shared configuration object used across the application.
config = AppConfig()
