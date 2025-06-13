# logic/renamer.py

import os
from datetime import datetime
from PySide6.QtWidgets import QMessageBox

from logic.settings import ItemSettings
from utils.file_utils import ensure_unique_name

class Renamer:
    def __init__(self, project: str, items: list[ItemSettings]):
        self.project = project
        self.items = items

    def build_mapping(self) -> list[tuple[ItemSettings, str, str]]:
        date_str = datetime.now().strftime("%y%m%d")
        mapping = []
        counter = 1
        for item in self.items:
            orig_path = item.original_path
            ordered_tags = list(item.tags)
            new_basename = item.build_new_name(self.project, counter, date_str, ordered_tags)
            dirpath = os.path.dirname(orig_path)
            candidate = os.path.join(dirpath, new_basename)
            unique = ensure_unique_name(candidate, orig_path)
            mapping.append((item, orig_path, unique))
            counter += 1
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
