from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List


class FileService:
    """Logic around managing the file list."""

    def __init__(self) -> None:
        self.files: List[Path] = []

    def add_files(self, paths: Iterable[str]) -> None:
        for p in paths:
            path = Path(p)
            if path.is_file() and path not in self.files:
                self.files.append(path)

    def clear(self) -> None:
        self.files.clear()

    def all_files(self) -> List[Path]:
        return list(self.files)

