"""
This module defines the `ItemSettings` dataclass, which encapsulates all relevant metadata
for a single file intended for renaming. It includes methods for serialization, date formatting,
and constructing new file names based on various project and tag configurations.
It also manages a list of globally accepted file extensions.
"""

import os
import logging
from dataclasses import dataclass, field
from datetime import datetime
import re

from .rename_config import RenameConfig
from .. import config_manager

logger = logging.getLogger(__name__)

# Load accepted extensions from config. Provide a default empty list if loading fails.
try:
    ACCEPT_EXTENSIONS = config_manager.get("accepted_extensions", [])
    if not ACCEPT_EXTENSIONS:
        logger.warning("'accepted_extensions' not found in config or is empty. Using a default set.")
        ACCEPT_EXTENSIONS = [
            ".jpg", ".jpeg", ".png", ".gif", ".bmp",
            ".mp4", ".avi", ".mov", ".mkv", ".heic" # Added .heic as it's handled by converter
        ]
except Exception as e:
    logger.error(f"Error loading 'accepted_extensions' from config: {e}. Using a default set.")
    ACCEPT_EXTENSIONS = [
        ".jpg", ".jpeg", ".png", ".gif", ".bmp",
        ".mp4", ".avi", ".mov", ".mkv", ".heic"
    ]


@dataclass
class ItemSettings:
    """
    Represents the settings and metadata for a single item (file) to be renamed.

    Attributes:
        original_path (str): The absolute path to the original file.
        tags (set[str]): A set of tags associated with the item, used for naming.
                         Defaults to an empty set.
        suffix (str): An optional suffix to be appended to the new file name.
                      Defaults to an empty string.
        date (str): A date string associated with the item (e.g., 'YYMMDD').
                    If not a 6-digit string, the current date will be used as a fallback.
                    Defaults to an empty string.
        position (str): An optional position string for specific renaming modes.
                        Defaults to an empty string.
        pa_mat (str): An optional PA_MAT (Project/Material) string for specific renaming modes.
                      Defaults to an empty string.
        size_bytes (int): The original size of the file in bytes. Defaults to 0.
        compressed_bytes (int): The size of the file after compression in bytes.
                                Defaults to 0.
    """
    original_path: str
    tags: set[str] = field(default_factory=set)
    suffix: str = ""
    date: str = ""
    position: str = ""
    pa_mat: str = ""
    size_bytes: int = 0
    compressed_bytes: int = 0

    def to_dict(self) -> dict:
        """
        Converts the ItemSettings object into a dictionary representation.

        Returns:
            dict: A dictionary containing the item's attributes, including the original filename.
        """
        return {
            "original_path": self.original_path,
            "original_filename": os.path.basename(self.original_path),
            "tags": list(self.tags),  # Convert set to list for JSON serialization
            "suffix": self.suffix,
            "date": self.date,
            "position": self.position,
            "pa_mat": self.pa_mat,
            "size_bytes": self.size_bytes,
            "compressed_bytes": self.compressed_bytes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ItemSettings':
        """
        Creates an ItemSettings object from a dictionary representation.

        Args:
            data (dict): A dictionary containing the item's attributes.
                         Must contain 'original_path'.

        Returns:
            ItemSettings: A new ItemSettings instance populated with data from the dictionary.

        Raises:
            KeyError: If 'original_path' is missing from the input dictionary.
        """
        try:
            return cls(
                original_path=data["original_path"], # 'original_path' is a mandatory field
                new_path=data.get("new_path", ""), # Added new_path from dict
                tags={tag.upper() for tag in data.get("tags", [])}, # Convert tags to uppercase set
                suffix=data.get("suffix", ""),
                date=data.get("date", ""),
                position=data.get("position", ""),
                pa_mat=data.get("pa_mat", ""),
                size_bytes=data.get("size_bytes", 0),
                compressed_bytes=data.get("compressed_bytes", 0),
            )
        except KeyError as e:
            logger.error(f"Missing required key in data for ItemSettings.from_dict: {e}. Data: {data}")
            raise # Re-raise to indicate a critical data integrity issue

    def _date_str(self, config: RenameConfig) -> str:
        """
        Generates a date string for the new file name.

        If `self.date` is a valid 6-digit string, it is used. Otherwise, the current date
        formatted according to `config.date_format` is used as a fallback.

        Args:
            config (RenameConfig): The renaming configuration containing the date format.

        Returns:
            str: The formatted date string.
        """
        # Check if the existing date is a valid 6-digit string (e.g., YYMMDD).
        if self.date and re.fullmatch(r"\d{6}", self.date):
            return self.date
        # If not valid, use the current date formatted according to the configuration.
        logger.info(f"Invalid or missing date '{self.date}' for {self.original_path}. Using current date.")
        return datetime.now().strftime(config.date_format)

    def build_base_name(
        self,
        project: str,
        ordered_tags: list[str],
        config: RenameConfig,
    ) -> str:
        """
        Builds the base name for the file, excluding index and suffix.

        The base name typically consists of the project name, ordered tags, and a date string,
        joined by the configured separator.

        Args:
            project (str): The project name.
            ordered_tags (list[str]): A list of tags, already sorted, to be included in the name.
            config (RenameConfig): The renaming configuration.

        Returns:
            str: The constructed base name.
        """
        # Get the date string, using fallback if necessary.
        date_str = self._date_str(config)
        # Combine project, ordered tags, and date string into parts.
        parts = [project] + ordered_tags + [date_str]
        # Join the parts with the configured separator to form the base name.
        base = config.separator.join(parts)
        return base

    def build_new_name(
        self,
        project: str,
        index: int,
        ordered_tags: list[str],
        config: RenameConfig,
        include_index: bool = True,
    ) -> str:
        """
        Builds the complete new file name, including base name, optional index, and optional suffix.

        Args:
            project (str): The project name.
            index (int): The sequential index for the file.
            ordered_tags (list[str]): A list of tags, already sorted.
            config (RenameConfig): The renaming configuration.
            include_index (bool): If True, the sequential index will be included in the name.
                                  Defaults to True.

        Returns:
            str: The complete new file name with its original extension.
        """
        # Build the base name first.
        base = self.build_base_name(project, ordered_tags, config)
        name = base
        # Append the padded index if required.
        if include_index:
            name += f"{config.separator}{index:0{config.index_padding}d}"
        # Append the suffix if present.
        if self.suffix:
            name += f"{config.separator}{self.suffix}"
        # Extract the original file extension.
        ext = os.path.splitext(self.original_path)[1]
        # Combine the new name with the original extension.
        return name + ext


# Backward compatibility: Assign ACCEPT_EXTENSIONS to ItemSettings class for older references.
# This ensures that any code still referencing ItemSettings.ACCEPT_EXTENSIONS continues to work.
ItemSettings.ACCEPT_EXTENSIONS = ACCEPT_EXTENSIONS


