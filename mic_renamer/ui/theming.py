from __future__ import annotations

from typing import Any

from PySide6.QtGui import QPalette, QColor

from ..config.config_manager import config_manager


class ThemeManager:
    """Apply colors defined in configuration globally."""

    def __init__(self) -> None:
        self.colors = config_manager.get_sub("theme", {})

    def reload(self) -> None:
        self.colors = config_manager.get_sub("theme", {})

    def apply_palette(self, widget) -> None:
        pal = widget.palette()
        bg = QColor(self.colors.get("background_white", "#ffffff"))
        primary = QColor(self.colors.get("primary_blue", "#2F6FDE"))
        pal.setColor(QPalette.Window, bg)
        pal.setColor(QPalette.Button, primary)
        widget.setPalette(pal)


# singleton
theme_manager = ThemeManager()

