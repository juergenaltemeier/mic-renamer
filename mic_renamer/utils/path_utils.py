"""Utility functions for application paths."""
from pathlib import Path
from appdirs import user_config_dir
import os

ENV_CONFIG_DIR = "RENAMER_CONFIG_DIR"


def get_config_dir() -> Path:
    """Return the directory used to store user configuration."""
    env_dir = os.environ.get(ENV_CONFIG_DIR)
    if env_dir:
        return Path(env_dir)
    return Path(user_config_dir("mic_renamer"))
