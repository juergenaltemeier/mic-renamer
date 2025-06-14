import json
import os

current_language = 'en'

_translations_cache: dict[str, dict[str, str]] = {}
_translations_dir: str | None = None


def _get_translations_dir() -> str:
    """Return directory where translation files are stored."""
    global _translations_dir
    if _translations_dir is None:
        default_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "translations")
        try:
            from ..config.app_config import load_config
            cfg = load_config()
            _translations_dir = cfg.get("translations_dir", default_dir)
        except Exception:
            _translations_dir = default_dir
    return _translations_dir


def _load_language(lang: str) -> dict[str, str]:
    if lang in _translations_cache:
        return _translations_cache[lang]
    dir_path = _get_translations_dir()
    path = os.path.join(dir_path, f"{lang}.json")
    data = {}
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    _translations_cache[lang] = data
    return data


def set_language(lang: str):
    """Set current language and load translations lazily."""
    global current_language
    _load_language(lang)
    current_language = lang


def tr(key: str) -> str:
    return _load_language(current_language).get(key, key)

