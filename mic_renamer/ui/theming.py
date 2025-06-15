from __future__ import annotations

"""Utility classes for loading and applying UI themes."""

from typing import Any
import logging

from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication

from ..config.config_manager import config_manager


def is_valid_color(value: str) -> bool:
    """Return ``True`` if ``value`` is a valid color string understood by ``QColor``."""
    if not isinstance(value, str):
        return False
    return QColor(value).isValid()


class ThemeManager:
    """Load colors from configuration and apply them as Qt palette/stylesheet."""

    DEFAULTS = {
        "primary_blue": "#2F6FDE",
        "background_white": "#FFFFFF",
        "accent_red": "#D94C4C",
        "text_color": "#000000",
        "base_color": "#FFFFFF",
        "alternate_base_color": "#F8F9FA",
        "button_text_color": "#FFFFFF",
        "highlight_color": "#2F6FDE",
        "highlight_text_color": "#FFFFFF",
        "debug_minimal": False,
    }

    def __init__(self) -> None:
        self.colors: dict[str, str] = {}
        self.debug_minimal = False
        self.reload()

    def reload(self) -> None:
        """Reload color values from the configuration with validation."""
        cfg = config_manager.get_sub("theme", {})
        self.debug_minimal = bool(cfg.get("debug_minimal", self.DEFAULTS["debug_minimal"]))
        self.colors = {}
        for key, default in self.DEFAULTS.items():
            if key == "debug_minimal":
                continue
            val = cfg.get(key, default)
            if not is_valid_color(val):
                logging.warning("Invalid color for %s: %s - using %s", key, val, default)
                val = default
            self.colors[key] = val

    def apply_palette(self) -> None:
        """Apply the base color palette to the ``QApplication`` instance."""
        app = QApplication.instance()
        if not app:
            return
        pal = app.palette()
        pal.setColor(QPalette.Window, QColor(self.colors["background_white"]))
        pal.setColor(QPalette.WindowText, QColor(self.colors["text_color"]))
        pal.setColor(QPalette.Base, QColor(self.colors["base_color"]))
        pal.setColor(QPalette.AlternateBase, QColor(self.colors["alternate_base_color"]))
        pal.setColor(QPalette.Text, QColor(self.colors["text_color"]))
        pal.setColor(QPalette.Button, QColor(self.colors["primary_blue"]))
        pal.setColor(QPalette.ButtonText, QColor(self.colors["button_text_color"]))
        pal.setColor(QPalette.Highlight, QColor(self.colors["highlight_color"]))
        pal.setColor(QPalette.HighlightedText, QColor(self.colors["highlight_text_color"]))
        app.setPalette(pal)

    def apply_widget_styles(self) -> None:
        app = QApplication.instance()
        if not app:
            return
        btn_style = (
            f"QPushButton {{"
            f" background-color: {self.colors['primary_blue']};"
            f" color: {self.colors['button_text_color']};"
            f" border-radius: 4px;"
            f" padding: 6px 12px;"
            f" }}"
        )
        btn_pressed = (
            f"QPushButton:pressed {{"
            f" background-color: {self._darken(self.colors['primary_blue'], 20)};"
            f" }}"
        )
        header_style = (
            f"QHeaderView::section {{"
            f" background-color: {self.colors['primary_blue']};"
            f" color: {self.colors['button_text_color']};"
            f" padding: 4px;"
            f" border: none;"
            f" }}"
        )
        select_style = (
            f"QTableView::item:selected, QTreeView::item:selected {{"
            f" background-color: {self.colors['highlight_color']};"
            f" color: {self.colors['highlight_text_color']};"
            f" }}"
        )
        style_sheet = "\n".join([btn_style, btn_pressed, header_style, select_style])
        app.setStyleSheet(style_sheet)

    def apply_theme_all(self) -> None:
        self.apply_palette()
        if not self.debug_minimal:
            self.apply_widget_styles()

    @staticmethod
    def _darken(hex_color: str, percent: int) -> str:
        """Return a darker shade of ``hex_color`` by ``percent``."""
        col = QColor(hex_color)
        r = max(0, int(col.red() * (100 - percent) / 100))
        g = max(0, int(col.green() * (100 - percent) / 100))
        b = max(0, int(col.blue() * (100 - percent) / 100))
        return QColor(r, g, b).name()


# singleton
theme_manager = ThemeManager()

