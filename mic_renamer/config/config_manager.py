"""Load and save user configuration."""
from __future__ import annotations

import yaml
from importlib import resources
from pathlib import Path

from ..utils.path_utils import get_config_dir


# Fallback defaults used when the bundled YAML file is missing. This ensures
# PyInstaller builds still work even if the data file was not included.
DEFAULTS_YAML = """
accepted_extensions:
  - .jpg
  - .jpeg
  - .png
  - .gif
  - .bmp
  - .heic
  - .mp4
  - .avi
  - .mov
  - .mkv
language: en
tags_file: tags.json
tag_usage_file: tag_usage.json
last_project_number: ""
tag_panel_visible: false
toolbar_style: icons
default_save_directory: ""
default_import_directory: ""
compression_max_size_kb: 2048
compression_quality: 95
compression_reduce_resolution: true
compression_resize_only: false
compression_max_width: 0
compression_max_height: 0
compress_after_rename: false
"""


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
        try:
            defaults_text = self.defaults_path.read_text()
        except FileNotFoundError:
            defaults_text = DEFAULTS_YAML
        defaults = yaml.safe_load(defaults_text)
        # ensure default path for the tags file in user config directory
        if "tags_file" not in defaults:
            defaults["tags_file"] = str(Path(get_config_dir()) / "tags.json")
        # default path for tag usage statistics
        if "tag_usage_file" not in defaults:
            defaults["tag_usage_file"] = str(Path(get_config_dir()) / "tag_usage.json")
        # directory used when choosing an alternative save location
        if "default_save_directory" not in defaults:
            defaults["default_save_directory"] = str(get_config_dir())
        if "default_import_directory" not in defaults:
            defaults["default_import_directory"] = ""
        # migrate legacy setting name
        if "compression_max_size_mb" in data and "compression_max_size_kb" not in data:
            data["compression_max_size_kb"] = float(data.pop("compression_max_size_mb")) * 1024
        self._config = {**defaults, **data}
        return self._config

    def save(self, cfg: dict | None = None) -> None:
        """Save configuration to disk."""
        if cfg is not None:
            self._config = cfg
        cfg = cfg or self._config
        if cfg is None:
            try:
                cfg_text = self.defaults_path.read_text()
            except FileNotFoundError:
                cfg_text = DEFAULTS_YAML
            cfg = yaml.safe_load(cfg_text)
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
        try:
            defaults_text = self.defaults_path.read_text()
        except FileNotFoundError:
            defaults_text = DEFAULTS_YAML
        defaults = yaml.safe_load(defaults_text)
        if "tags_file" not in defaults:
            defaults["tags_file"] = str(Path(get_config_dir()) / "tags.json")
        if "tag_usage_file" not in defaults:
            defaults["tag_usage_file"] = str(Path(get_config_dir()) / "tag_usage.json")
        if "default_save_directory" not in defaults:
            defaults["default_save_directory"] = str(get_config_dir())
        if "default_import_directory" not in defaults:
            defaults["default_import_directory"] = ""
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
        usage_file = cfg.get("tag_usage_file")
        if usage_file:
            usage_path = Path(usage_file)
            if not usage_path.is_absolute():
                usage_path = Path(get_config_dir()) / usage_path
            if not usage_path.is_file():
                try:
                    save_counts({})
                except Exception:
                    pass
