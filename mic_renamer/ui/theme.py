from __future__ import annotations

"""Application wide theme utilities."""

from importlib import resources

from PySide6.QtGui import QPalette, QColor, QIcon
from PySide6.QtWidgets import QApplication, QStyle
from PySide6.QtCore import Qt


def create_dark_palette() -> QPalette:
    """Return a dark ``QPalette`` used across the application."""
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    return palette


def apply_dark_theme(app: QApplication) -> None:
    """Apply Fusion style and dark palette to ``app``."""
    app.setStyle("Fusion")
    app.setPalette(create_dark_palette())


def themed_icon(name: str, fallback: QStyle.StandardPixmap) -> QIcon:
    """Return a themed ``QIcon`` or fallback standard icon."""
    icon = QIcon.fromTheme(name)
    if not icon.isNull():
        return icon
    style = QApplication.style()
    return style.standardIcon(fallback)


def resource_icon(name: str) -> QIcon:
    """Load an icon from the bundled resources folder."""
    path = resources.files("mic_renamer.resources.icons") / name
    return QIcon(str(path))
