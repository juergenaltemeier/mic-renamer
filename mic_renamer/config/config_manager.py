"""Load and save user configuration."""
from __future__ import annotations

from pathlib import Path
from importlib import resources
import yaml

from ..utils.path_utils import get_config_dir


class ConfigManager:
    """Manage application configuration."""

    def __init__(self):
        self.config_dir = get_config_dir()
        self.config_file = Path(self.config_dir) / "app_settings.yaml"
        self._config: dict | None = None
        # load defaults via importlib.resources so PyInstaller bundles work
        self.defaults_path = resources.files(__package__) / "defaults.yaml"

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
        # ensure default path for the tags file in user config directory
        defaults.setdefault("tags_file", str(Path(get_config_dir()) / "tags.json"))
        # default path for tag usage statistics
        defaults.setdefault("tag_usage_file", str(Path(get_config_dir()) / "tag_usage.json"))
        # directory used when choosing an alternative save location
        defaults.setdefault("default_save_directory", str(get_config_dir()))
        # migrate legacy setting name
        if "compression_max_size_mb" in data and "compression_max_size_kb" not in data:
            data["compression_max_size_kb"] = float(data.pop("compression_max_size_mb")) * 1024
        defaults.setdefault("compression_max_size_kb", 2048)
        defaults.setdefault("compression_quality", 95)
        defaults.setdefault("compression_reduce_resolution", True)
        defaults.setdefault("compression_resize_only", False)
        defaults.setdefault("compression_max_width", 0)
        defaults.setdefault("compression_max_height", 0)
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

    def restore_defaults(self) -> dict:
        """Overwrite config file with bundled defaults."""
        defaults = yaml.safe_load(self.defaults_path.read_text())
        defaults.setdefault("tags_file", str(Path(get_config_dir()) / "tags.json"))
        defaults.setdefault("tag_usage_file", str(Path(get_config_dir()) / "tag_usage.json"))
        defaults.setdefault("default_save_directory", str(get_config_dir()))
        defaults.setdefault("compression_max_size_kb", 2048)
        defaults.setdefault("compression_quality", 95)
        defaults.setdefault("compression_reduce_resolution", True)
        defaults.setdefault("compression_resize_only", False)
        defaults.setdefault("compression_max_width", 0)
        defaults.setdefault("compression_max_height", 0)
        self._config = defaults
        self.save(defaults)
        return defaults

    def ensure_files(self) -> None:
        """Create config and related files on first run."""
        cfg = self.load()
        # ensure config file exists on disk
        if not Path(self.config_file).is_file():
            self.save(cfg)
        # ensure tags and usage files exist
        from ..logic.tag_loader import restore_default_tags
        from ..logic.tag_usage import save_counts
        restore_default_tags()
        usage_path = Path(cfg.get("tag_usage_file"))
        if not usage_path.is_absolute():
            usage_path = Path(get_config_dir()) / usage_path
        if not usage_path.is_file():
            try:
                save_counts({})
            except Exception:
                pass
