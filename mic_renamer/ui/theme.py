from __future__ import annotations

from importlib import resources

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QStyle
from . import styles
from .. import config_manager


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
    is_dark = config_manager.get("theme", "dark") == "dark"
    
    if is_dark:
        app.setStyleSheet(app.styleSheet() + """
            /* base tag box style */
            *[class=\"tag-box\"] {
                border: 1px solid #555;
                border-radius: 12px;
                background-color: #444;
                padding: 10px 15px;
            }
            *[class=\"tag-box\"]:hover {
                border: 1px solid #009ee0;
                background-color: #555;
            }
            /* checked tag box style */
            *[class=\"tag-box-checked\"] {
                border: 1px solid #009ee0;
                border-radius: 12px;
                background-color: #009ee0;
                padding: 10px 15px;
            }
            *[class=\"tag-box-checked\"]:hover {
                border: 1px solid #00b8ff;
                background-color: #008bd4;
            }
            /* preselected tag box style */
            *[class=\"tag-box-preselected\"] {
                border: 2px solid #00b8ff;
                border-radius: 12px;
                background-color: #444;
                padding: 10px 15px;
            }
            /* description label styling */
            *[class=\"tag-box\"] QLabel#TagDesc {
                color: #ccc;
            }
            /* code label styling */
            *[class=\"tag-box\"] QLabel#TagCode {
                color: palette(text);
                font-weight: bold;
            }
            /* checked state styling */
            *[class=\"tag-box-checked\"] QLabel#TagDesc,
            *[class=\"tag-box-checked\"] QLabel#TagCode {
                color: #ffffff;
            }
        """)
    else:
        app.setStyleSheet(app.styleSheet() + """
            /* base tag box style */
            *[class=\"tag-box\"] {
                border: 1px solid #ccc;
                border-radius: 12px;
                background-color: #f0f0f0;
                padding: 10px 15px;
            }
            *[class=\"tag-box\"]:hover {
                border: 1px solid #009ee0;
                background-color: #e0e0e0;
            }
            /* checked tag box style */
            *[class=\"tag-box-checked\"] {
                border: 1px solid #009ee0;
                border-radius: 12px;
                background-color: #009ee0;
                padding: 10px 15px;
            }
            *[class=\"tag-box-checked\"]:hover {
                border: 1px solid #00b8ff;
                background-color: #008bd4;
            }
            /* preselected tag box style */
            *[class=\"tag-box-preselected\"] {
                border: 2px solid #00b8ff;
                border-radius: 12px;
                background-color: #f0f0f0;
                padding: 10px 15px;
            }
            /* description label styling */
            *[class=\"tag-box\"] QLabel#TagDesc {
                color: #333;
            }
            /* code label styling */
            *[class=\"tag-box\"] QLabel#TagCode {
                color: palette(text);
                font-weight: bold;
            }
            /* checked state styling */
            *[class=\"tag-box-checked\"] QLabel#TagDesc,
            *[class=\"tag-box-checked\"] QLabel#TagCode {
                color: #ffffff;
            }
        """)


def apply_styles(app: QApplication, theme: str = "dark") -> None:
    """Apply all styles to the application."""
    app.setStyle("Fusion")
    
    if theme == "dark":
        qss_path = resources.files(styles) / "dark_style.qss"
    else:
        qss_path = resources.files(styles) / "shadcn_style.qss"
        
    with qss_path.open("r") as f:
        app.setStyleSheet(f.read())
        
    apply_tag_box_style(app)

