"""Photo/Video renamer package."""

from .config.app_config import load_config, save_config
from .utils.i18n import set_language

# load configuration on import
config = load_config()
set_language(config.get("language", "en"))

__all__ = ["config", "save_config"]

