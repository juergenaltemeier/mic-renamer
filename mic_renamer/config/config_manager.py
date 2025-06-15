from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from appdirs import user_config_dir


class ConfigManager:
    """Load and save application configuration."""

    def __init__(self, app_name: str = "MicRenamer") -> None:
        self.app_name = app_name
        self.config_dir = Path(os.environ.get("RENAMER_CONFIG_DIR", user_config_dir(app_name))).expanduser()
        self.config_file = self.config_dir / "config.yaml"
        self.defaults_file = Path(__file__).with_name("defaults.yaml")
        self._data: dict[str, Any] = {}

    def load(self) -> None:
        """Load configuration from disk, falling back to defaults."""
        self._data = {}
        try:
            if self.config_file.is_file():
                with self.config_file.open("r", encoding="utf-8") as fh:
                    self._data = yaml.safe_load(fh) or {}
        except Exception as exc:
            logging.warning("Failed to load config %s: %s", self.config_file, exc)
            self._data = {}
        if not self._data:
            try:
                with self.defaults_file.open("r", encoding="utf-8") as fh:
                    self._data = yaml.safe_load(fh) or {}
            except Exception as exc:
                logging.error("Failed to load defaults: %s", exc)
                self._data = {}

    def get(self, key: str, default: Any | None = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def save(self) -> None:
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with self.config_file.open("w", encoding="utf-8") as fh:
                yaml.safe_dump(self._data, fh)
        except Exception as exc:
            logging.error("Failed to save config %s: %s", self.config_file, exc)

    # Extra helpers
    def get_sub(self, section: str, default: dict[str, Any] | None = None) -> dict[str, Any]:
        val = self._data.get(section)
        if isinstance(val, dict):
            return val
        return default or {}


# Convenience singleton
config_manager = ConfigManager()
config_manager.load()
