"""Photo/Video renamer package."""

from .config.app_config import load_config, save_config
from .config.theme_config import load_theme
from .utils.i18n import set_language

# load configuration on import
config = load_config()
set_language(config.get("language", "en"))
theme = load_theme()

__all__ = ["config", "theme", "save_config"]

