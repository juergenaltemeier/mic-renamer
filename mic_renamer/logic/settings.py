# logic/settings.py

import os
from dataclasses import dataclass, field
from datetime import datetime
import re


class RenameConfig:
    """Configuration for building new file names."""

    date_format: str = "%y%m%d"
    index_padding: int = 3
    separator: str = "_"
    start_index: int = 1


from .. import config_manager

# load accepted extensions from config
ACCEPT_EXTENSIONS = config_manager.get("accepted_extensions", [
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
])


@dataclass
class ItemSettings:
    original_path: str
    tags: set[str] = field(default_factory=set)
    suffix: str = ""
    date: str = ""

    def _date_str(self, config: RenameConfig) -> str:
        if self.date and re.fullmatch(r"\d{6}", self.date):
            return self.date
        return datetime.now().strftime(config.date_format)

    def build_base_name(
        self,
        project: str,
        ordered_tags: list[str],
        config: RenameConfig,
    ) -> str:
        date_str = self._date_str(config)
        parts = [project] + ordered_tags + [date_str]
        base = config.separator.join(parts)
        if self.suffix:
            base += f"{config.separator}{self.suffix}"
        return base

    def build_new_name(
        self,
        project: str,
        index: int,
        ordered_tags: list[str],
        config: RenameConfig,
        include_index: bool = True,
    ) -> str:
        base = self.build_base_name(project, ordered_tags, config)
        if include_index:
            base += f"{config.separator}{index:0{config.index_padding}d}"
        ext = os.path.splitext(self.original_path)[1]
        return base + ext


# backward compatibility
ItemSettings.ACCEPT_EXTENSIONS = ACCEPT_EXTENSIONS


