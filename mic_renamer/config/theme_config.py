import os
import yaml
from .app_config import get_config_dir

THEME_FILE = os.path.join(get_config_dir(), "theme.yaml")

DEFAULT_THEME = {
    "primary_blue": "#0055AA",
    "background_white": "#F8F9FA",
    "accent_red": "#CC3333",
}

_theme = None


def load_theme() -> dict:
    """Load theme colors from configuration file."""
    global _theme
    if _theme is not None:
        return _theme
    data = {}
    if os.path.isfile(THEME_FILE):
        try:
            with open(THEME_FILE, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
                if isinstance(loaded, dict):
                    data = loaded.get("theme", loaded)
        except Exception:
            data = {}
    _theme = {**DEFAULT_THEME, **data}
    return _theme
