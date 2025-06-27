# logic/settings.py

import os
from dataclasses import dataclass, field
from datetime import datetime
import re

from .rename_config import RenameConfig
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
    position: str = ""
    pa_mat: str = ""
    size_bytes: int = 0
    compressed_bytes: int = 0

    def to_dict(self):
        return {
            "original_path": self.original_path,
            "original_filename": os.path.basename(self.original_path),
            "tags": list(self.tags),
            "suffix": self.suffix,
            "date": self.date,
            "position": self.position,
            "pa_mat": self.pa_mat,
            "size_bytes": self.size_bytes,
            "compressed_bytes": self.compressed_bytes,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            original_path=data["original_path"],
            tags=set(data.get("tags", [])),
            suffix=data.get("suffix", ""),
            date=data.get("date", ""),
            position=data.get("position", ""),
            pa_mat=data.get("pa_mat", ""),
            size_bytes=data.get("size_bytes", 0),
            compressed_bytes=data.get("compressed_bytes", 0),
        )

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
        name = base
        if include_index:
            name += f"{config.separator}{index:0{config.index_padding}d}"
        if self.suffix:
            name += f"{config.separator}{self.suffix}"
        ext = os.path.splitext(self.original_path)[1]
        return name + ext


# backward compatibility
ItemSettings.ACCEPT_EXTENSIONS = ACCEPT_EXTENSIONS


