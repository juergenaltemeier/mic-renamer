"""
This module provides the `StateManager` class, which is responsible for persisting
and retrieving application UI state, such as window geometry, settings, and other
user preferences. It uses a JSON file for storage and includes robust error handling
for file I/O operations.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class StateManager:
    """
    Manages the persistence of UI state, such as window geometry and other application settings.

    The state is stored in a JSON file within a specified directory.
    """

    def __init__(self, directory: Path):
        """
        Initializes the StateManager.

        Args:
            directory (Path): The absolute path to the directory where the state file
                              (state.json) will be stored. This directory will be created
                              if it does not exist.
        """
        # Define the full path to the state file.
        self.path = directory / "state.json"
        logger.info(f"StateManager initialized. State file path: {self.path}")
        # Load the initial state from the file or initialize an empty state.
        self.state = self._load()

    def _load(self) -> dict[str, Any]:
        """
        Loads the application state from the state file (`state.json`).

        If the file does not exist, an empty dictionary is returned. Handles potential
        file I/O errors and JSON decoding errors gracefully.

        Returns:
            dict[str, Any]: A dictionary containing the loaded state. Returns an empty
                            dictionary if the file is not found or loading fails.
        """
        # Check if the state file exists.
        if not self.path.is_file():
            logger.info(f"State file not found at {self.path}. Initializing with empty state.")
            return {}

        try:
            # Open and load the JSON data from the state file.
            with self.path.open("r", encoding="utf-8") as f:
                state_data = json.load(f)
            if isinstance(state_data, dict):
                logger.info(f"Successfully loaded state from {self.path}.")
                return state_data
            else:
                logger.warning(f"State file {self.path} contains invalid JSON format (not a dictionary). Returning empty state.")
                return {}
        except FileNotFoundError:
            # This case should ideally be caught by `self.path.is_file()` but included for robustness.
            logger.warning(f"State file not found at {self.path} during load attempt. Returning empty state.")
            return {}
        except json.JSONDecodeError as e:
            # Log errors if the JSON content is malformed.
            logger.error(f"Failed to decode JSON from state file {self.path}: {e}. Returning empty state.")
            return {}
        except IOError as e:
            # Log general I/O errors during file reading.
            logger.error(f"IO Error loading state from {self.path}: {e}. Returning empty state.")
            return {}
        except Exception as e:
            # Catch any other unexpected errors during loading.
            logger.error(f"An unexpected error occurred while loading state from {self.path}: {e}. Returning empty state.")
            return {}

    def save(self) -> None:
        """
        Saves the current application state to the state file (`state.json`).

        Ensures that the parent directory for the state file exists before attempting
        to write. Handles potential file I/O errors gracefully.
        """
        try:
            # Ensure the parent directory exists. `parents=True` creates any missing parent directories.
            # `exist_ok=True` prevents an error if the directory already exists.
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # Open the file in write mode and dump the current state as JSON with indentation.
            with self.path.open("w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
            logger.info(f"Successfully saved state to {self.path}.")
        except (IOError, OSError) as e:
            # Log errors related to file writing or directory creation.
            logger.error(f"Failed to save state to {self.path}: {e}")
        except json.JSONEncodeError as e:
            # Log errors if the state dictionary cannot be serialized to JSON.
            logger.error(f"Failed to encode state to JSON for {self.path}: {e}")
        except Exception as e:
            # Catch any other unexpected errors during saving.
            logger.error(f"An unexpected error occurred while saving state to {self.path}: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a value from the current application state.

        Args:
            key (str): The key of the state variable to retrieve.
            default (Any): The default value to return if the key is not found in the state.
                           Defaults to None.

        Returns:
            Any: The value associated with the key, or the default value if the key is not found.
        """
        return self.state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Sets or updates a value in the application state.

        Args:
            key (str): The key of the state variable to set.
            value (Any): The value to associate with the key.
        """
        self.state[key] = value
        logger.debug(f"State key '{key}' set to '{value}'")

