"""Load and save user configuration."""
from __future__ import annotations

from pathlib import Path
import yaml

from ..utils.path_utils import get_config_dir


class ConfigManager:
    """Manage application configuration."""

    def __init__(self):
        self.config_dir = get_config_dir()
        self.config_file = Path(self.config_dir) / "app_settings.yaml"
        self._config: dict | None = None
        self.defaults_path = Path(__file__).with_name("defaults.yaml")

    def load(self) -> dict:
        """Load configuration from disk merging with defaults."""
        if self._config is not None:
            return self._config
        data = {}
        if self.config_file.is_file():
            try:
                data = yaml.safe_load(self.config_file.read_text()) or {}
            except Exception:
                data = {}
        defaults = yaml.safe_load(self.defaults_path.read_text())
        self._config = {**defaults, **data}
        return self._config

    def save(self, cfg: dict | None = None) -> None:
        """Save configuration to disk."""
        if cfg is not None:
            self._config = cfg
        cfg = cfg or self._config
        if cfg is None:
            cfg = yaml.safe_load(self.defaults_path.read_text())
        Path(self.config_dir).mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as fh:
            yaml.safe_dump(cfg, fh)

    # convenience helpers
    def get(self, key: str, default=None):
        return self.load().get(key, default)

    def set(self, key: str, value) -> None:
        cfg = self.load()
        cfg[key] = value
        self.save(cfg)
