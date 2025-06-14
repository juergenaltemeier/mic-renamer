import json
import os

DEFAULT_TAGS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "tags.json")

def load_tags(file_path: str = DEFAULT_TAGS_FILE) -> dict:
    """Load tag definitions from a JSON file."""
    if not os.path.isfile(file_path):
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

