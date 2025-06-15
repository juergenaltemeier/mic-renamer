"""Persist and load simple UI state like window geometry."""
import json
from pathlib import Path


class StateManager:
    def __init__(self, directory: Path):
        self.path = Path(directory) / "state.json"
        self.state = self._load()

    def _load(self) -> dict:
        if self.path.is_file():
            try:
                return json.loads(self.path.read_text())
            except Exception:
                return {}
        return {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as fh:
            json.dump(self.state, fh, indent=2)

    def get(self, key: str, default=None):
        return self.state.get(key, default)

    def set(self, key: str, value) -> None:
        self.state[key] = value
