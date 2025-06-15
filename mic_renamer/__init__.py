"""Photo/Video renamer package."""
from .config.config_manager import ConfigManager
from .utils.i18n import set_language

config_manager = ConfigManager()
config = config_manager.load()
set_language(config.get("language", "en"))

__all__ = ["config_manager", "config"]
