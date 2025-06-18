import json
import os
from pathlib import Path
from importlib import resources

from .. import config_manager
from ..utils.path_utils import get_config_dir

DEFAULT_TAGS_FILE = Path(get_config_dir()) / "tags.json"
BUNDLED_TAGS_FILE = resources.files("mic_renamer.config") / "tags.json"

CONFIG_TAGS_FILE = config_manager.get("tags_file")

ENV_TAGS_FILE = "RENAMER_TAGS_FILE"


def _load_raw(file_path: str | None = None) -> dict:
    """Internal helper returning the raw tag dictionary."""
    if file_path is None:
        file_path = os.environ.get(ENV_TAGS_FILE) or CONFIG_TAGS_FILE or DEFAULT_TAGS_FILE
    path = Path(file_path)
    if not path.is_absolute():
        path = Path(get_config_dir()) / path
    if not path.is_file():
        if path == DEFAULT_TAGS_FILE:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(BUNDLED_TAGS_FILE.read_text(), encoding="utf-8")
            except Exception:
                pass
    if not path.is_file():
        path = BUNDLED_TAGS_FILE
    if not path.is_file():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}

def load_tags(file_path: str | None = None, language: str | None = None) -> dict:
    """Return tags for the requested language.

    If the file contains translations for multiple languages the appropriate
    entry is returned. When only a plain string is present, it is used for all
    languages.
    """
    raw = _load_raw(file_path)
    lang = language or config_manager.get("language", "en")
    result = {}
    for code, value in raw.items():
        if isinstance(value, str):
            result[code] = value
        elif isinstance(value, dict):
            result[code] = value.get(lang) or next(iter(value.values()), "")
    return result


def load_tags_multilang(file_path: str | None = None) -> dict:
    """Return the raw tag dictionary with translations."""
    return _load_raw(file_path)


def restore_default_tags() -> None:
    """Reset the user's tags.json to the bundled defaults."""
    try:
        DEFAULT_TAGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_TAGS_FILE.write_text(BUNDLED_TAGS_FILE.read_text(), encoding="utf-8")
    except Exception:
        pass


