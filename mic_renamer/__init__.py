"""Photo/Video renamer package."""

from .config.config_manager import config_manager
from .utils.i18n import set_language

config_manager.load()
set_language(config_manager.get("language", "en"))

__all__ = ["config_manager"]

