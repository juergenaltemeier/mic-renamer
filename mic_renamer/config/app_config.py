import json
import os

PACKAGE_ROOT = os.path.dirname(os.path.dirname(__file__))
CONFIG_FILE = os.path.join(PACKAGE_ROOT, "config", "app_settings.json")
TRANSLATIONS_DIR = os.path.join(PACKAGE_ROOT, "config", "translations")

DEFAULT_CONFIG = {
    "accepted_extensions": [
        ".jpg", ".jpeg", ".png", ".gif", ".bmp",
        ".mp4", ".avi", ".mov", ".mkv"
    ],
    "language": "en",
    "translations_dir": TRANSLATIONS_DIR
}

_config = None

def load_config():
    global _config
    if _config is not None:
        return _config
    data = {}
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    _config = {**DEFAULT_CONFIG, **data}
    return _config


def save_config(cfg=None):
    global _config
    if cfg is not None:
        _config = cfg
    else:
        cfg = _config
    if cfg is None:
        cfg = DEFAULT_CONFIG
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

