from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable

from ..config.config_manager import config_manager

_PACKAGE_DIR = Path(__file__).resolve().parents[1]


def _tags_path() -> Path:
    cfg = config_manager
    return cfg.config_dir / "tags.json"


class TagService:
    """Load and persist tag information."""

    def __init__(self) -> None:
        self.tags: Dict[str, str] = {}
        self.load()

    def load(self) -> None:
        """Load tag definitions from the user config directory.

        If no tags file exists in the user directory, fall back to the
        bundled default ``tags.json`` shipped with the package. This mirrors
        the behaviour of the pre-refactored version where default tags were
        always available.
        """
        path = _tags_path()
        if not path.is_file():
            default_path = _PACKAGE_DIR / "config" / "tags.json"
            path = default_path
        if path.is_file():
            try:
                with path.open("r", encoding="utf-8") as fh:
                    self.tags = json.load(fh)
            except Exception as exc:
                raise RuntimeError(f"Failed to load tags: {exc}") from exc
        else:
            self.tags = {}

    def save(self) -> None:
        path = _tags_path()
        try:
            with path.open("w", encoding="utf-8") as fh:
                json.dump(self.tags, fh, indent=2)
        except Exception as exc:
            raise RuntimeError(f"Failed to save tags: {exc}") from exc

    def all_tags(self) -> Dict[str, str]:
        return dict(self.tags)


# singleton
tag_service = TagService()

