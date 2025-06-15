from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config.config_manager import config_manager


class StateManager:
    """Persist UI runtime state (e.g., window geometry)."""

    def __init__(self) -> None:
        cfg_dir = config_manager.config_dir
        self.state_file = cfg_dir / "state.json"
        self._data: dict[str, Any] = {}

    def load(self) -> None:
        if self.state_file.is_file():
            try:
                self._data = json.loads(self.state_file.read_text(encoding="utf-8"))
            except Exception:
                self._data = {}

    def save(self) -> None:
        try:
            self.state_file.write_text(json.dumps(self._data), encoding="utf-8")
        except Exception:
            pass

    def get(self, key: str, default: Any | None = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value


state_manager = StateManager()

