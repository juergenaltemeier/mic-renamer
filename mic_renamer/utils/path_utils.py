"""
This module provides utility functions for determining and managing application-specific
file paths, particularly for user configuration directories. It ensures that the application
can locate and store its configuration files in a platform-appropriate and user-configurable manner.
"""
from __future__ import annotations

import os
import logging
from pathlib import Path

from appdirs import user_config_dir

logger = logging.getLogger(__name__)

# Environment variable name that can be used to override the default configuration directory.
ENV_CONFIG_DIR = "RENAMER_CONFIG_DIR"


def get_config_dir() -> Path:
    """
    Determines the appropriate directory for storing user configuration files.

    This function follows a specific hierarchy to find the configuration directory:
    1.  It first checks if the `RENAMER_CONFIG_DIR` environment variable is set.
        If it is, that path is used.
    2.  If the environment variable is not set, it falls back to the standard user
        configuration directory for the application, as determined by `appdirs.user_config_dir`.

    The function also ensures that the determined directory exists, creating it if necessary.

    Returns:
        Path: A Path object representing the absolute path to the configuration directory.

    Raises:
        OSError: If the determined configuration directory cannot be created.
    """
    config_dir: Path

    # 1. Check for environment variable override.
    if env_dir := os.environ.get(ENV_CONFIG_DIR):
        config_dir = Path(env_dir)
        logger.debug(f"Using config directory from environment variable: {config_dir}")
    else:
        # 2. Fallback to standard user configuration directory.
        config_dir = Path(user_config_dir("mic_renamer"))
        logger.debug(f"Using default user config directory: {config_dir}")
    
    # Ensure the configuration directory exists.
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured config directory exists at: {config_dir}")
    except OSError as e:
        logger.error(f"Failed to create configuration directory {config_dir}: {e}")
        # Re-raise the exception as this is a critical failure for the application.
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred while ensuring config directory exists at {config_dir}: {e}")
        raise

    return config_dir

