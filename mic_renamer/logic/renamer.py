# logic/renamer.py

import os
from collections import defaultdict
from PySide6.QtWidgets import QMessageBox

from .settings import ItemSettings, RenameConfig
from ..utils.file_utils import ensure_unique_name

class Renamer:
    def __init__(self, project: str, items: list[ItemSettings], config: RenameConfig | None = None):
        self.project = project
        self.items = items
        self.config = config or RenameConfig()

    def build_mapping(self) -> list[tuple[ItemSettings, str, str]]:
        """Build the rename mapping for all items."""
        groups: dict[str, list[tuple[ItemSettings, list[str]]]] = defaultdict(list)
        for item in self.items:
            ordered_tags = sorted(item.tags)
            base = item.build_base_name(self.project, ordered_tags, self.config)
            groups[base].append((item, ordered_tags))

        mapping = []
        for base, items in groups.items():
            use_index = len(items) > 1
            counter = self.config.start_index
            for item, ordered_tags in items:
                new_basename = item.build_new_name(
                    self.project,
                    counter,
                    ordered_tags,
                    self.config,
                    include_index=use_index,
                )
                if use_index:
                    counter += 1
                dirpath = os.path.dirname(item.original_path)
                candidate = os.path.join(dirpath, new_basename)
                unique = ensure_unique_name(candidate, item.original_path)
                mapping.append((item, item.original_path, unique))

        return mapping

    def execute_rename(self, mapping: list[tuple[ItemSettings, str, str]], parent_widget):
        for item, orig, new in mapping:
            try:
                orig_abs = os.path.abspath(orig)
                new_abs = os.path.abspath(new)
                if orig_abs != new_abs:
                    os.rename(orig, new)
                    item.original_path = new
            except Exception as e:
                QMessageBox.warning(
                    parent_widget,
                    "Rename Failed",
                    f"Fehler beim Umbenennen:\n{orig}\n→ {new}\nError: {e}"
                )
