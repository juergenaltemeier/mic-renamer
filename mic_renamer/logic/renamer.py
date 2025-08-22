# logic/renamer.py

import os
from collections import defaultdict
from pathlib import Path

from .settings import ItemSettings
from .rename_config import RenameConfig
from ..utils.file_utils import ensure_unique_name

class Renamer:
    """
    The Renamer class is responsible for generating a mapping of old file paths to new file paths
    based on various renaming modes and configurations. It handles different naming conventions
    including position-based, PA_MAT-based, and tag-based renaming.
    """

    def __init__(self, project: str, items: list[ItemSettings], config: RenameConfig | None = None,
                 dest_dir: str | None = None, mode: str = "normal"):
        """
        Initializes the Renamer with project details, items to rename, and configuration.

        Args:
            project (str): The project name to be used in the new file names.
            items (list[ItemSettings]): A list of ItemSettings objects, each representing a file
                                        to be renamed with its associated metadata.
            config (RenameConfig | None): An optional RenameConfig object containing renaming rules
                                          like start index, separator, and index padding.
                                          If None, a default RenameConfig is used.
            dest_dir (str | None): An optional destination directory for the renamed files.
                                   If None, files are renamed in their original directories.
            mode (str): The renaming mode to apply. Supported modes are "normal", "position",
                        and "pa_mat". Defaults to "normal".
        """
        self.project = project
        self.items = items
        self.dest_dir = dest_dir
        # Use provided config or initialize with default RenameConfig
        self.config = config or RenameConfig()
        self.mode = mode

    def _generate_unique_path(self, original_path: str, new_basename: str) -> str:
        """
        Generates a unique file path for the new basename within the destination directory.

        Args:
            original_path (str): The original path of the item.
            new_basename (str): The proposed new base name (filename + extension).

        Returns:
            str: A unique absolute path for the renamed file.
        """
        try:
            # Determine the directory for the new file. If dest_dir is not set, use the original file's directory.
            dirpath = self.dest_dir or os.path.dirname(original_path)
            # Convert original_path to Path object for use with pathlib functions.
            original_path_obj = Path(original_path)
            # Construct the full candidate path for the new file.
            candidate_str = os.path.join(dirpath, new_basename)
            # Convert candidate_str to Path object for use with pathlib functions.
            candidate_obj = Path(candidate_str)
            # Ensure the generated name is unique to prevent overwriting existing files.
            unique_path = ensure_unique_name(candidate_obj, original_path_obj)
            return str(unique_path) # Return as string as per function signature.
        except OSError as e:
            # Handle potential OS errors during path manipulation or uniqueness check.
            print(f"Error generating unique path for {original_path} with new basename {new_basename}: {e}")
            # Log the error and return None to indicate failure in generating a unique path.
            return None

    def _build_position_mapping(self) -> list[tuple[ItemSettings, str, str]]:
        """
        Builds the rename mapping for "position" mode.
        In this mode, files are grouped by a base name derived from the project and an optional suffix,
        and then indexed sequentially within each group.

        Returns:
            list[tuple[ItemSettings, str, str]]: A list of tuples, where each tuple contains
                                                  (item_settings, original_path, new_unique_path).
        """
        # Group items based on a generated base name.
        # The base name combines the project name with "_pos" and an optional suffix from the item.
        # This ensures that files logically belonging together (e.g., multiple images from the same
        # project with a specific suffix) are grouped for sequential indexing.
        groups: dict[str, list[ItemSettings]] = defaultdict(list)
        for item in self.items:
            base = f"{self.project}_pos"
            if item.suffix:
                base += f"_{item.suffix}"
            groups[base].append(item)

        mapping: list[tuple[ItemSettings, str, str]] = []
        # Process each group to generate unique new names.
        for base, items_in_group in groups.items():
            # An index is appended to the base name only if there's more than one item in the group.
            # This prevents unnecessary indexing for single files.
            use_index = len(items_in_group) > 1
            # Initialize the counter for sequential indexing, starting from the configured start_index.
            counter = self.config.start_index
            for item in items_in_group:
                name = base
                # If indexing is required, append the formatted counter to the name.
                # The counter is formatted with leading zeros based on index_padding for consistent naming.
                if use_index:
                    name += f"{self.config.separator}{counter:0{self.config.index_padding}d}"
                    counter += 1
                # Extract the original file extension to preserve it in the new file name.
                ext = os.path.splitext(item.original_path)[1]
                new_basename = name + ext
                # Attempt to generate a unique absolute path for the new file.
                unique = self._generate_unique_path(item.original_path, new_basename)
                if unique is None:
                    # If a unique path could not be generated, skip this item and log a warning.
                    print(f"Warning: Skipping item {item.original_path} due to failure in generating a unique path.")
                    continue
                # Add the original item settings, original path, and the newly generated unique path
                # to the mapping list.
                mapping.append((item, item.original_path, unique))
        return mapping

    def _build_pa_mat_mapping(self) -> list[tuple[ItemSettings, str, str]]:
        """
        Builds the rename mapping for "pa_mat" mode.
        Files are grouped by their PA_MAT value or date, and then indexed sequentially within each group.

        Returns:
            list[tuple[ItemSettings, str, str]]: A list of tuples, where each tuple contains
                                                  (item_settings, original_path, new_unique_path).
        """
        # Group items by their `pa_mat` attribute or `date` attribute if `pa_mat` is not present.
        # This groups files that are logically related by a common identifier or creation date,
        # allowing for sequential indexing within these groups.
        groups: dict[str, list[ItemSettings]] = defaultdict(list)
        for item in self.items:
            key = item.pa_mat or item.date
            groups[key].append(item)

        mapping: list[tuple[ItemSettings, str, str]] = []
        # Process each group to generate unique new names.
        for key, items_in_group in groups.items():
            # An index is appended to the base name only if there's more than one item in the group.
            # This prevents unnecessary indexing for single files.
            use_index = len(items_in_group) > 1
            # Initialize the counter for sequential indexing, starting from the configured start_index.
            counter = self.config.start_index
            for item in items_in_group:
                # Construct the base name including the project name and the `pa_mat` or date key.
                base = f"{self.project}_PA_MAT_{key}"
                # If indexing is required, append the formatted counter to the base name.
                # The counter is formatted with leading zeros based on `index_padding` for consistent naming.
                if use_index:
                    base += f"{self.config.separator}{counter:0{self.config.index_padding}d}"
                    counter += 1
                # Append the item's suffix if it exists, separated by the configured separator.
                if item.suffix:
                    base += f"{self.config.separator}{item.suffix}"
                # Extract the original file extension to preserve it in the new file name.
                ext = os.path.splitext(item.original_path)[1]
                new_basename = base + ext
                # Attempt to generate a unique absolute path for the new file.
                unique = self._generate_unique_path(item.original_path, new_basename)
                if unique is None:
                    # If a unique path could not be generated, skip this item and log a warning.
                    print(f"Warning: Skipping item {item.original_path} due to failure in generating a unique path.")
                    continue
                # Add the original item settings, original path, and the newly generated unique path
                # to the mapping list.
                mapping.append((item, item.original_path, unique))
        return mapping

    def _build_default_mapping(self) -> list[tuple[ItemSettings, str, str]]:
        """
        Builds the rename mapping for the default mode (tag-based).
        Files are grouped by their generated base name (which includes project and sorted tags),
        and then indexed sequentially within each group if multiple items share the same base name.

        Returns:
            list[tuple[ItemSettings, str, str]]: A list of tuples, where each tuple contains
                                                  (item_settings, original_path, new_unique_path).
        """
        # Group items by their calculated base name. The base name is constructed from the project
        # name and a sorted list of the item's tags. This ensures consistent grouping for files
        # that share the same project and tags, regardless of the original order of tags.
        groups: dict[str, list[tuple[ItemSettings, list[str]]]] = defaultdict(list)
        for item in self.items:
            # Ensure tags are sorted for consistent base name generation. This is crucial because
            # the order of tags might vary, but the logical grouping should be based on the set of tags.
            ordered_tags = sorted(list(item.tags))
            # Build the base name using the item's `build_base_name` method, which incorporates
            # the project name, ordered tags, and configuration settings.
            base = item.build_base_name(self.project, ordered_tags, self.config)
            groups[base].append((item, ordered_tags))

        mapping = []
        # Process each group to generate unique new names.
        for base, items_in_group in groups.items():
            # An index is appended to the new file name only if there's more than one item in the group.
            # This prevents unnecessary indexing for single files.
            use_index = len(items_in_group) > 1
            # Initialize the counter for sequential indexing, starting from the configured `start_index`.
            counter = self.config.start_index
            for item, ordered_tags in items_in_group:
                # Build the new file name using the item's `build_new_name` method. This method
                # handles the inclusion of the project name, counter (if `use_index` is true),
                # ordered tags, and configuration settings.
                new_basename = item.build_new_name(
                    self.project,
                    counter,
                    ordered_tags,
                    self.config,
                    include_index=use_index,
                )
                # Increment the counter only if an index was actually used for the current item.
                if use_index:
                    counter += 1
                # Attempt to generate a unique absolute path for the new file.
                unique = self._generate_unique_path(item.original_path, new_basename)
                if unique is None:
                    # If a unique path could not be generated, skip this item and log a warning.
                    print(f"Warning: Skipping item {item.original_path} due to failure in generating a unique path.")
                    continue
                # Add the original item settings, original path, and the newly generated unique path
                # to the mapping list.
                mapping.append((item, item.original_path, unique))
        return mapping

    def build_mapping(self) -> list[tuple[ItemSettings, str, str]]:
        """
        Builds the rename mapping for all items based on the configured mode.

        Returns:
            list[tuple[ItemSettings, str, str]]: A list of tuples, where each tuple contains
                                                  (item_settings, original_path, new_unique_path).
                                                  Returns an empty list if an invalid mode is specified.
        """
        if self.mode == "position":
            return self._build_position_mapping()
        elif self.mode == "pa_mat":
            return self._build_pa_mat_mapping()
        elif self.mode == "normal":
            return self._build_default_mapping()
        else:
            # Handle unknown mode gracefully by printing a warning and returning an empty list.
            # This prevents the program from crashing and allows for continued operation.
            print(f"Warning: Unknown renaming mode '{self.mode}'. No mapping will be generated.")
            return []

