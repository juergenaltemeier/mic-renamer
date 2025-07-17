# logic/renamer.py

import os
from collections import defaultdict

from .settings import ItemSettings
from .rename_config import RenameConfig
from ..utils.file_utils import ensure_unique_name

class Renamer:
    def __init__(self, project: str, items: list[ItemSettings], config: RenameConfig | None = None,
                 dest_dir: str | None = None, mode: str = "normal"):
        self.project = project
        self.items = items
        self.dest_dir = dest_dir
        self.config = config or RenameConfig()
        self.mode = mode

    def build_mapping(self) -> list[tuple[ItemSettings, str, str]]:
        """Build the rename mapping for all items."""
        if self.mode == "position":
            groups: dict[str, list[ItemSettings]] = defaultdict(list)
            for item in self.items:
                base = f"{self.project}_pos"
                if item.suffix:
                    base += f"_{item.suffix}"
                groups[base].append(item)

            mapping: list[tuple[ItemSettings, str, str]] = []
            for base, items_in_group in groups.items():
                use_index = len(items_in_group) > 1
                counter = self.config.start_index
                for item in items_in_group:
                    name = base
                    if use_index:
                        name += f"{self.config.separator}{counter:0{self.config.index_padding}d}"
                        counter += 1
                    ext = os.path.splitext(item.original_path)[1]
                    new_basename = name + ext
                    dirpath = self.dest_dir or os.path.dirname(item.original_path)
                    candidate = os.path.join(dirpath, new_basename)
                    unique = ensure_unique_name(candidate, item.original_path)
                    mapping.append((item, item.original_path, unique))
            return mapping
        if self.mode == "pa_mat":
            groups: dict[str, list[ItemSettings]] = defaultdict(list)
            for item in self.items:
                key = item.pa_mat or item.date
                groups[key].append(item)

            mapping: list[tuple[ItemSettings, str, str]] = []
            for key, items_in_group in groups.items():
                use_index = len(items_in_group) > 1
                counter = self.config.start_index
                for item in items_in_group:
                    base = f"{self.project}_PA_MAT{key}"
                    if use_index:
                        base += f"{self.config.separator}{counter:0{self.config.index_padding}d}"
                        counter += 1
                    if item.suffix:
                        base += f"{self.config.separator}{item.suffix}"
                    ext = os.path.splitext(item.original_path)[1]
                    new_basename = base + ext
                    dirpath = self.dest_dir or os.path.dirname(item.original_path)
                    candidate = os.path.join(dirpath, new_basename)
                    unique = ensure_unique_name(candidate, item.original_path)
                    mapping.append((item, item.original_path, unique))
            return mapping

        groups: dict[str, list[tuple[ItemSettings, list[str]]]] = defaultdict(list)
        for item in self.items:
            ordered_tags = sorted(list(item.tags))
            base = item.build_base_name(self.project, ordered_tags, self.config)
            groups[base].append((item, ordered_tags))

        mapping = []
        for base, items_in_group in groups.items():
            use_index = len(items_in_group) > 1
            counter = self.config.start_index
            for item, ordered_tags in items_in_group:
                new_basename = item.build_new_name(
                    self.project,
                    counter,
                    ordered_tags,
                    self.config,
                    include_index=use_index,
                )
                if use_index:
                    counter += 1
                dirpath = self.dest_dir or os.path.dirname(item.original_path)
                candidate = os.path.join(dirpath, new_basename)
                unique = ensure_unique_name(candidate, item.original_path)
                mapping.append((item, item.original_path, unique))

        return mapping
