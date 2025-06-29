from __future__ import annotations

from importlib import resources

from PySide6.QtGui import QPalette, QColor, QIcon
from PySide6.QtWidgets import QApplication, QStyle
from PySide6.QtCore import Qt

"""Application wide theme utilities."""

# guessed brand colors from micavac.com
BRAND_PRIMARY = QColor("#009ee0")
BRAND_SECONDARY = QColor("#ff6600")


def create_dark_palette() -> QPalette:
    """Return a dark ``QPalette`` used across the application."""
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(45, 45, 45))
    palette.setColor(QPalette.AlternateBase, QColor(60, 60, 60))
    palette.setColor(QPalette.ToolTipBase, QColor(60, 60, 60))
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, BRAND_PRIMARY)
    # use a brighter shade for selected cells
    palette.setColor(QPalette.Highlight, BRAND_PRIMARY.lighter(210))
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


def apply_tag_box_style(app: QApplication) -> None:
    app.setStyleSheet(app.styleSheet() + """
        .tag-box {
            border: 1px solid #555;
            border-radius: 12px; /* More rounded corners */
            background-color: #444; /* Darker filled background */
            padding: 10px 15px; /* Medium size padding */
        }
        .tag-box:hover {
            border: 1px solid #009ee0;
            background-color: #555; /* Slightly lighter on hover */
        }
        .tag-box-checked {
            border: 1px solid #009ee0;
            border-radius: 12px;
            background-color: #009ee0; /* Solid blue for active */
            padding: 10px 15px;
        }
        .tag-box-checked:hover {
            border: 1px solid #00b8ff;
            background-color: #008bd4; /* Slightly darker blue on hover */
        }
        .tag-box-preselected {
            border: 2px solid #00b8ff; /* Bright blue border for pre-selection */
            border-radius: 12px;
            background-color: #444;
            padding: 10px 15px;
        }
        TagBox QLabel {
            color: #ccc;
        }
        TagBox QCheckBox {
            color: #eee;
            font-weight: bold;
        }
        .tag-box-checked QLabel, .tag-box-checked QCheckBox {
            color: #ffffff; /* White text for checked state */
        }
    """)
