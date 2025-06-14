import json
import os

from ..config.app_config import get_config_dir, load_config

DEFAULT_TAGS_FILE = os.path.join(get_config_dir(), "tags.json")

try:
    CONFIG_TAGS_FILE = load_config().get("tags_file")
except Exception:
    CONFIG_TAGS_FILE = None

ENV_TAGS_FILE = "RENAMER_TAGS_FILE"

def load_tags(file_path: str | None = None) -> dict:
    """Load tag definitions from a JSON file."""
    if file_path is None:
        file_path = os.environ.get(ENV_TAGS_FILE, CONFIG_TAGS_FILE or DEFAULT_TAGS_FILE)
    if not os.path.isfile(file_path):
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


