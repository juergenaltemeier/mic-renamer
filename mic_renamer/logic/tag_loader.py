import json
import os
from pathlib import Path

from .. import config_manager
from ..utils.path_utils import get_config_dir

DEFAULT_TAGS_FILE = Path(get_config_dir()) / "tags.json"
BUNDLED_TAGS_FILE = Path(__file__).resolve().parent.parent / "config" / "tags.json"

CONFIG_TAGS_FILE = config_manager.get("tags_file")

ENV_TAGS_FILE = "RENAMER_TAGS_FILE"

def load_tags(file_path: str | None = None) -> dict:
    """Load tag definitions from a JSON file."""
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
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


