"""Track and persist tag usage statistics."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .. import config_manager
from ..utils.path_utils import get_config_dir


def _get_usage_path() -> Path:
    path = Path(config_manager.get("tag_usage_file", "tag_usage.json"))
    if not path.is_absolute():
        path = Path(get_config_dir()) / path
    return path


def load_counts() -> dict[str, int]:
    path = _get_usage_path()
    if path.is_file():
        try:
            return json.loads(path.read_text())
        except Exception:
            return {}
    return {}


def save_counts(counts: dict[str, int]) -> None:
    path = _get_usage_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(counts, fh, indent=2)


def increment_tags(tags: Iterable[str]) -> None:
    counts = load_counts()
    for tag in tags:
        counts[tag] = counts.get(tag, 0) + 1
    save_counts(counts)


def reset_counts() -> None:
    save_counts({})
