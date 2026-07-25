from pathlib import Path


class FileCache:
    def __init__(self, path: str):
        self.path = Path(path)

        if not self.path.exists():
            self.path.touch()

        self._cache = self._load()

    def _load(self) -> set[str]:
        with self.path.open("r", encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip()}

    def contains(self, value: str) -> bool:
        return value in self._cache

    def add(self, value: str):
        if value in self._cache:
            return

        with self.path.open("a", encoding="utf-8") as f:
            f.write(f"{value}\n")

        self._cache.add(value)
