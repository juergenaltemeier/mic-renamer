from __future__ import annotations

from typing import Any
import logging

from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication

from ..config.config_manager import config_manager


def is_valid_color(value: str) -> bool:
    """Return True if the given string can be interpreted as a QColor."""
    if not isinstance(value, str):
        return False
    col = QColor(value)
    return col.isValid()


class ThemeManager:
    """Apply colors defined in configuration globally."""

    DEFAULTS = {
        "primary_blue": "#2F6FDE",
        "background_white": "#FFFFFF",
        "accent_red": "#D94C4C",
        "text_color": "#000000",
        "debug_minimal": False,
    }

    def __init__(self) -> None:
        self.colors: dict[str, str] = {}
        self.debug_minimal = False
        self.reload()

    def reload(self) -> None:
        cfg = config_manager.get_sub("theme", {})
        self.debug_minimal = bool(cfg.get("debug_minimal", self.DEFAULTS["debug_minimal"]))
        self.colors = {}
        for key in ["primary_blue", "background_white", "accent_red", "text_color"]:
            val = cfg.get(key, self.DEFAULTS[key])
            if not is_valid_color(val):
                logging.warning("Invalid color for %s: %s - using %s", key, val, self.DEFAULTS[key])
                val = self.DEFAULTS[key]
            self.colors[key] = val

    def apply_palette(self) -> None:
        app = QApplication.instance()
        if not app:
            return
        pal = QApplication.palette()
        pal.setColor(QPalette.Window, QColor(self.colors["background_white"]))
        pal.setColor(QPalette.WindowText, QColor(self.colors["text_color"]))
        app.setPalette(pal)

    def apply_widget_styles(self) -> None:
        app = QApplication.instance()
        if not app:
            return
        btn_style = (
            f"QPushButton {{ background-color: {self.colors['primary_blue']}; color: {self.colors['text_color']}; }}"
        )
        header_style = (
            f"QHeaderView::section {{ background-color: {self.colors['primary_blue']}; color: {self.colors['text_color']}; }}"
        )
        select_style = (
            f"QTableView::item:selected, QTableWidget::item:selected {{ background-color: {self.colors['accent_red']}; color: {self.colors['text_color']}; }}"
        )
        app.setStyleSheet("\n".join([btn_style, header_style, select_style]))

    def apply_theme_all(self) -> None:
        self.apply_palette()
        if not self.debug_minimal:
            self.apply_widget_styles()


# singleton
theme_manager = ThemeManager()

