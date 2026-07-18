import json
from pathlib import Path


# Class responsible for loading and accessing application configuration.
class AppConfig:
    def __init__(self):
        self.path = Path("filter_keywords.json")
        self._data = self._load()

    # Loads configuration data from a JSON file.
    def _load(self):
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    # Returns a list of values from configuration using nested keys.
    def get_list(self, keys: list[str]):
        current = self._data
        for key in keys:
            current = current.get(key, {})
        return current if isinstance(current, list) else []


# Creates a shared configuration object used across the application.
config = AppConfig()
