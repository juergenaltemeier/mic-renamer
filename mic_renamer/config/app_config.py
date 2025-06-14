import json
import os
import shutil
from appdirs import user_config_dir

PACKAGE_ROOT = os.path.dirname(os.path.dirname(__file__))

# Environment variable to override the configuration directory
ENV_CONFIG_DIR = "RENAMER_CONFIG_DIR"


def get_config_dir() -> str:
    """Return the directory used to store user configuration."""
    env_dir = os.environ.get(ENV_CONFIG_DIR)
    if env_dir:
        return env_dir
    return user_config_dir("mic-renamer")


# old config location inside the package directory (pre 1.1)
OLD_CONFIG_DIR = os.path.join(PACKAGE_ROOT, "config")
CONFIG_DIR = get_config_dir()
CONFIG_FILE = os.path.join(CONFIG_DIR, "app_settings.json")


def _migrate_legacy_config():
    """Move configuration files from the old location if present."""
    old_cfg = os.path.join(OLD_CONFIG_DIR, "app_settings.json")
    if os.path.isfile(old_cfg) and not os.path.isfile(CONFIG_FILE):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        shutil.move(old_cfg, CONFIG_FILE)

    old_tags = os.path.join(OLD_CONFIG_DIR, "tags.json")
    new_tags = os.path.join(CONFIG_DIR, "tags.json")
    if os.path.isfile(old_tags) and not os.path.isfile(new_tags):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        shutil.move(old_tags, new_tags)

DEFAULT_CONFIG = {
    "accepted_extensions": [
        ".jpg", ".jpeg", ".png", ".gif", ".bmp",
        ".mp4", ".avi", ".mov", ".mkv"
    ],
    "language": "en"
}

_config = None

def load_config():
    global _config
    if _config is not None:
        return _config
    _migrate_legacy_config()
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

