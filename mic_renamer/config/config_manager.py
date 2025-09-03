"""
This module provides the `ConfigManager` class, which is responsible for loading,
saving, and managing the application's configuration settings. It handles merging
user-specific settings with bundled default values, ensures configuration files
exist, and provides convenience methods for accessing and modifying settings.
Robust error handling is implemented for file I/O and YAML parsing.
"""
from __future__ import annotations

import yaml
import logging
from importlib import resources
from pathlib import Path
from typing import Any, Dict, Optional

from ..utils.path_utils import get_config_dir

logger = logging.getLogger(__name__)

# Fallback default configuration in YAML string format.
# This is used when the bundled `defaults.yaml` file cannot be found,
# ensuring the application can still run with a baseline configuration.
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
compression_max_size_kb: 2500
compression_quality: 99
compression_reduce_resolution: true
compression_resize_only: false
compression_max_width: 1440
compression_max_height: 1440
compress_after_rename: false
"""


class ConfigManager:
    """
    Manages application configuration, including loading from defaults, user settings,
    and saving changes. It handles file paths for configuration and ensures data integrity.
    """

    def __init__(self):
        """
        Initializes the ConfigManager.

        It determines the user's configuration directory and the path to the main
        application settings file (`app_settings.yaml`). It also sets up the path
        to the bundled default configuration file.
        """
        self.config_dir: Path = get_config_dir()
        self.config_file: Path = self.config_dir / "app_settings.yaml"
        self._config: Optional[Dict[str, Any]] = None # Cache for loaded configuration.
        
        # Path to the bundled default configuration file within the package resources.
        # This is crucial for PyInstaller builds to correctly locate default settings.
        self.defaults_path: Path = resources.files(__package__) / "defaults.yaml"
        logger.info(f"ConfigManager initialized. Config directory: {self.config_dir}, Config file: {self.config_file}")

    def get_defaults_path(self) -> Path:
        """
        Returns the absolute path to the bundled default configuration file.

        Returns:
            Path: The path to `defaults.yaml` within the application's resources.
        """
        return self.defaults_path

    def load(self) -> Dict[str, Any]:
        """
        Loads the application configuration.

        This method first loads default settings (from bundled file or hardcoded fallback),
        then merges them with user-specific settings from `app_settings.yaml`.
        User settings override defaults. It also handles migration of legacy settings
        and ensures default paths for related files (tags, tag usage) are set correctly.

        Returns:
            Dict[str, Any]: The merged configuration dictionary.
        """
        # Return cached configuration if already loaded.
        if self._config is not None:
            return self._config

        user_data: Dict[str, Any] = {}
        # 1. Load user-specific configuration from `app_settings.yaml`.
        if self.config_file.is_file():
            try:
                # Load YAML content. `or {}` handles empty files.
                user_data = yaml.safe_load(self.config_file.read_text(encoding="utf-8")) or {}
                logger.info(f"Successfully loaded user config from {self.config_file}.")
            except FileNotFoundError:
                logger.warning(f"User config file not found at {self.config_file}. Will use defaults.")
            except yaml.YAMLError as e:
                logger.error(f"Error parsing YAML in user config file {self.config_file}: {e}. Ignoring user config.")
            except Exception as e:
                logger.error(f"An unexpected error occurred loading user config from {self.config_file}: {e}. Ignoring user config.")

        defaults_text: str
        # 2. Load default configuration.
        try:
            defaults_text = self.defaults_path.read_text(encoding="utf-8")
            logger.debug(f"Loaded defaults from bundled file: {self.defaults_path}")
        except FileNotFoundError:
            # Fallback to hardcoded defaults if the bundled file is missing.
            logger.warning(f"Bundled defaults file not found at {self.defaults_path}. Using hardcoded defaults.")
            defaults_text = DEFAULTS_YAML
        except Exception as e:
            logger.error(f"An unexpected error occurred reading bundled defaults: {e}. Using hardcoded defaults.")
            defaults_text = DEFAULTS_YAML

        defaults: Dict[str, Any]
        try:
            defaults = yaml.safe_load(defaults_text) or {}
        except yaml.YAMLError as e:
            logger.critical(f"Error parsing hardcoded/bundled default YAML: {e}. Application may not function correctly.")
            defaults = {} # Critical error, but try to proceed with empty defaults.

        # Ensure default paths for tags and tag usage files are absolute and in the config directory.
        # This handles cases where defaults might be relative or missing.
        if "tags_file" not in defaults or not Path(defaults["tags_file"]).is_absolute():
            defaults["tags_file"] = str(self.config_dir / "tags.json")
            logger.debug(f"Set default tags_file to: {defaults['tags_file']}")
        
        if "tag_usage_file" not in defaults or not Path(defaults["tag_usage_file"]).is_absolute():
            defaults["tag_usage_file"] = str(self.config_dir / "tag_usage.json")
            logger.debug(f"Set default tag_usage_file to: {defaults['tag_usage_file']}")

        # Ensure default save directory is set to the config directory if not specified.
        if "default_save_directory" not in defaults or not defaults["default_save_directory"]:
            defaults["default_save_directory"] = str(self.config_dir)
            logger.debug(f"Set default_save_directory to: {defaults['default_save_directory']}")
        
        # Ensure default import directory is initialized.
        if "default_import_directory" not in defaults:
            defaults["default_import_directory"] = ""
            logger.debug("Initialized default_import_directory to empty string.")

        # Migrate legacy setting name: compression_max_size_mb to compression_max_size_kb.
        if "compression_max_size_mb" in user_data and "compression_max_size_kb" not in user_data:
            try:
                mb_value = float(user_data.pop("compression_max_size_mb"))
                user_data["compression_max_size_kb"] = mb_value * 1024
                logger.info(f"Migrated compression_max_size_mb to compression_max_size_kb: {mb_value}MB -> {user_data['compression_max_size_kb']}KB")
            except (ValueError, TypeError) as e:
                logger.error(f"Failed to migrate compression_max_size_mb due to invalid value: {e}")

        # Merge defaults with user data. User data takes precedence.
        self._config = {**defaults, **user_data}
        logger.info("Configuration loaded and merged.")
        return self._config

    def save(self, cfg: Optional[Dict[str, Any]] = None) -> None:
        """
        Saves the current configuration to the `app_settings.yaml` file on disk.

        Args:
            cfg (Optional[Dict[str, Any]]): The configuration dictionary to save.
                                            If None, the currently loaded configuration (`self._config`)
                                            is used. If `self._config` is also None, defaults are loaded.
        """
        # Use provided config, or current config, or load defaults if no config is present.
        config_to_save = cfg or self._config
        if config_to_save is None:
            logger.warning("No configuration provided or loaded. Loading defaults for saving.")
            config_to_save = self.load() # Load defaults if nothing is set.

        try:
            # Ensure the configuration directory exists before saving.
            self.config_dir.mkdir(parents=True, exist_ok=True)
            # Write the configuration to the YAML file.
            with open(self.config_file, "w", encoding="utf-8") as fh:
                yaml.safe_dump(config_to_save, fh, indent=2) # Use indent for readability.
            logger.info(f"Configuration successfully saved to {self.config_file}.")
            self._config = config_to_save # Update cached config after successful save.
        except (IOError, OSError) as e:
            logger.error(f"Failed to save configuration to {self.config_file}: {e}")
        except yaml.YAMLError as e:
            logger.error(f"Error encoding configuration to YAML for {self.config_file}: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred while saving configuration to {self.config_file}: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration value by its key.

        Automatically loads the configuration if it hasn't been loaded yet.

        Args:
            key (str): The key of the configuration setting to retrieve.
            default (Any): The default value to return if the key is not found.
                           Defaults to None.

        Returns:
            Any: The value associated with the key, or the provided default value.
        """
        return self.load().get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Sets or updates a configuration value and immediately saves the configuration to disk.

        Args:
            key (str): The key of the configuration setting to set.
            value (Any): The new value for the setting.
        """
        cfg = self.load()
        cfg[key] = value
        self.save(cfg)
        logger.debug(f"Config key '{key}' set to '{value}' and saved.")

    def restore_defaults(self) -> Dict[str, Any]:
        """
        Resets the application configuration to its bundled default values.

        This overwrites the user's `app_settings.yaml` file with the default content.
        It also ensures that default paths for tags and tag usage files are correctly set.

        Returns:
            Dict[str, Any]: The restored default configuration dictionary.
        """
        logger.info("Restoring configuration to default values.")
        defaults_text: str
        try:
            defaults_text = self.defaults_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.warning(f"Bundled defaults file not found at {self.defaults_path}. Using hardcoded defaults for restore.")
            defaults_text = DEFAULTS_YAML
        except Exception as e:
            logger.error(f"An unexpected error occurred reading bundled defaults for restore: {e}. Using hardcoded defaults.")
            defaults_text = DEFAULTS_YAML

        defaults: Dict[str, Any]
        try:
            defaults = yaml.safe_load(defaults_text) or {}
        except yaml.YAMLError as e:
            logger.critical(f"Error parsing default YAML during restore: {e}. Returning empty defaults.")
            return {} # Critical error, cannot restore defaults properly.

        # Ensure default paths are correctly set after loading defaults.
        if "tags_file" not in defaults or not Path(defaults["tags_file"]).is_absolute():
            defaults["tags_file"] = str(self.config_dir / "tags.json")
        if "tag_usage_file" not in defaults or not Path(defaults["tag_usage_file"]).is_absolute():
            defaults["tag_usage_file"] = str(self.config_dir / "tag_usage.json")
        if "default_save_directory" not in defaults or not defaults["default_save_directory"]:
            defaults["default_save_directory"] = str(self.config_dir)
        if "default_import_directory" not in defaults:
            defaults["default_import_directory"] = ""

        self._config = defaults # Update the cached configuration.
        self.save(defaults) # Save the restored defaults to disk.

        # Also restore the default tags file to bundled defaults.
        try:
            from ..logic.tag_loader import restore_default_tags
            restore_default_tags()
            logger.info("Tags restored to bundled defaults.")
        except Exception as e:
            logger.error(f"Failed to restore default tags during restore_defaults: {e}")

        logger.info("Configuration successfully restored to defaults.")
        return defaults

    def ensure_files(self) -> None:
        """
        Ensures that essential configuration and data files exist on the disk.

        This method is typically called on application startup to create `app_settings.yaml`,
        `tags.json`, and `tag_usage.json` if they are missing. It leverages other modules'
        functions for creating default tag and usage files.
        """
        logger.info("Ensuring essential configuration files exist.")
        cfg = self.load()
        
        # Ensure the main config file (`app_settings.yaml`) exists on disk.
        if not self.config_file.is_file():
            logger.info(f"Config file {self.config_file} not found. Saving current config to create it.")
            self.save(cfg)
        
        # Ensure tags and tag usage files exist. Only create defaults if missing.
        try:
            from ..logic.tag_loader import (
                BUNDLED_TAGS_FILE,
                BUNDLED_TAGS_JSON,
            )
            from ..logic.tag_usage import save_counts

            # Determine configured tags file path (absolute)
            tags_file_str = cfg.get("tags_file", "tags.json")
            tags_path = Path(tags_file_str)
            if not tags_path.is_absolute():
                tags_path = self.config_dir / tags_path

            if not tags_path.is_file():
                logger.info(f"Tags file not found at {tags_path}. Creating from defaults once.")
                try:
                    tags_path.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        # Prefer bundled file when available
                        tags_path.write_text(BUNDLED_TAGS_FILE.read_text(encoding="utf-8"), encoding="utf-8")
                    except Exception:
                        # Fallback to embedded JSON
                        tags_path.write_text(BUNDLED_TAGS_JSON, encoding="utf-8")
                    logger.info(f"Created default tags file at {tags_path}.")
                except Exception as e:
                    logger.error(f"Failed to create default tags file at {tags_path}: {e}")

            # Ensure the tag usage file exists and is initialized (if not already).
            usage_file_path_str = cfg.get("tag_usage_file")
            if usage_file_path_str:
                usage_path = Path(usage_file_path_str)
                if not usage_path.is_absolute():
                    usage_path = self.config_dir / usage_path
                if not usage_path.is_file():
                    logger.info(f"Tag usage file {usage_path} not found. Initializing with empty counts.")
                    try:
                        save_counts({})
                    except Exception as e:
                        logger.error(f"Failed to initialize tag usage file {usage_path}: {e}")
            else:
                logger.warning("'tag_usage_file' setting is missing in config. Cannot ensure its existence.")
        except ImportError as e:
            logger.error(f"Failed to import dependencies for file assurance: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during file assurance: {e}")
