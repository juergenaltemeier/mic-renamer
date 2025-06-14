import json
import os

PACKAGE_ROOT = os.path.dirname(os.path.dirname(__file__))
DEFAULT_TAGS_FILE = os.path.join(PACKAGE_ROOT, "config", "tags.json")

ENV_TAGS_FILE = "RENAMER_TAGS_FILE"

def load_tags(file_path: str | None = None) -> dict:
    """Load tag definitions from a JSON file."""
    if file_path is None:
        file_path = os.environ.get(ENV_TAGS_FILE, DEFAULT_TAGS_FILE)
    if not os.path.isfile(file_path):
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


