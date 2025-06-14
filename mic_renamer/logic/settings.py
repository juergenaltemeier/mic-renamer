# logic/settings.py

import os
from dataclasses import dataclass, field


class RenameConfig:
    """Configuration for building new file names."""

    date_format: str = "%y%m%d"
    index_padding: int = 3
    separator: str = "_"
    start_index: int = 1


from ..config.app_config import load_config

# load accepted extensions from config
ACCEPT_EXTENSIONS = load_config().get("accepted_extensions", [
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

    def build_new_name(
        self,
        project: str,
        index: int,
        date_str: str,
        ordered_tags: list[str],
        config: RenameConfig,
    ) -> str:
        parts = [project] + ordered_tags + [date_str, f"{index:0{config.index_padding}d}"]
        base = config.separator.join(parts)
        if self.suffix:
            base += f"{config.separator}{self.suffix}"
        ext = os.path.splitext(self.original_path)[1]
        return base + ext


# backward compatibility
ItemSettings.ACCEPT_EXTENSIONS = ACCEPT_EXTENSIONS


