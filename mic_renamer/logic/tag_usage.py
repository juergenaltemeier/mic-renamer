"""
This module manages the tracking and persistence of tag usage statistics within the
mic-renamer application. It provides functions to load, save, increment, and reset
tag usage counts, storing them in a JSON file in the user's configuration directory.
Robust error handling and logging are implemented for file operations.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable

from .. import config_manager
from ..utils.path_utils import get_config_dir

logger = logging.getLogger(__name__)


def _get_usage_path() -> Path:
    """
    Internal helper function to determine the absolute path to the tag usage JSON file.

    The path is resolved by first checking the `tag_usage_file` setting in the
    application's configuration manager. If the configured path is relative, it's
    resolved against the user's configuration directory.

    Returns:
        Path: The absolute path to the `tag_usage.json` file.
    """
    # Get the configured path for the tag usage file, defaulting to "tag_usage.json".
    path = Path(config_manager.get("tag_usage_file", "tag_usage.json"))
    # If the path is not absolute, resolve it relative to the user's config directory.
    if not path.is_absolute():
        path = Path(get_config_dir()) / path
    return path


def get_usage_path() -> Path:
    """
    Returns the absolute path to the `tag_usage.json` file.

    This function exposes the internal path resolution logic for external use.

    Returns:
        Path: The absolute path to the `tag_usage.json` file.
    """
    return _get_usage_path()


def load_counts() -> dict[str, int]:
    """
    Loads tag usage counts from the `tag_usage.json` file.

    Handles cases where the file does not exist or contains invalid JSON data.

    Returns:
        dict[str, int]: A dictionary where keys are tag names (uppercase) and values
                        are their usage counts. Returns an empty dictionary if the
                        file is not found, is corrupted, or an error occurs during loading.
    """
    path = _get_usage_path()
    if path.is_file():
        try:
            # Attempt to read and parse the JSON file.
            counts = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(counts, dict):
                logger.info(f"Successfully loaded tag usage counts from {path}.")
                return counts
            else:
                logger.warning(f"Tag usage file {path} contains invalid format (not a dictionary). Returning empty counts.")
                return {}
        except FileNotFoundError:
            # This case should ideally be caught by path.is_file() but included for robustness.
            logger.warning(f"Tag usage file not found at {path}. Returning empty counts.")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from tag usage file {path}: {e}. Returning empty counts.")
            return {}
        except OSError as e:
            logger.error(f"OS error reading tag usage file {path}: {e}. Returning empty counts.")
            return {}
        except Exception as e:
            logger.error(f"An unexpected error occurred while loading tag usage counts from {path}: {e}. Returning empty counts.")
            return {}
    else:
        logger.info(f"Tag usage file not found at {path}. Initializing with empty counts.")
        return {}


def save_counts(counts: dict[str, int]) -> None:
    """
    Saves tag usage counts to the `tag_usage.json` file.

    Ensures the parent directory exists before writing the file.

    Args:
        counts (dict[str, int]): A dictionary of tag names and their usage counts to be saved.
    """
    path = _get_usage_path()
    try:
        # Ensure the parent directory exists. `exist_ok=True` prevents error if it already exists.
        path.parent.mkdir(parents=True, exist_ok=True)
        # Open the file in write mode and dump the JSON data with indentation for readability.
        with path.open("w", encoding="utf-8") as fh:
            json.dump(counts, fh, indent=2)
        logger.info(f"Successfully saved tag usage counts to {path}.")
    except (OSError, IOError) as e:
        logger.error(f"Error writing tag usage counts to {path}: {e}")
    except json.JSONEncodeError as e:
        logger.error(f"Error encoding tag usage counts to JSON for {path}: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while saving tag usage counts to {path}: {e}")


def increment_tags(tags: Iterable[str]) -> None:
    """
    Increments the usage count for each specified tag.

    Tags are converted to uppercase before incrementing to ensure case-insensitive tracking.
    The updated counts are then saved to the `tag_usage.json` file.

    Args:
        tags (Iterable[str]): A collection of tag names whose counts are to be incremented.
    """
    # Load current counts.
    counts = load_counts()
    # Increment each tag's count. If a tag is new, it starts at 0 before incrementing.
    for tag in tags:
        counts[tag.upper()] = counts.get(tag.upper(), 0) + 1
    # Save the updated counts.
    save_counts(counts)


def reset_counts() -> None:
    """
    Resets all tag usage counts to zero.

    This is achieved by saving an empty dictionary to the `tag_usage.json` file.
    """
    logger.info("Resetting all tag usage counts.")
    save_counts({})
