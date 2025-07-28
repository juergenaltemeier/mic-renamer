"""
This module provides functions for managing and applying visual themes and icons
within the mic-renamer application. It supports loading icons from bundled resources,
applying dynamic QSS (Qt Style Sheets) based on selected themes (dark/light),
and ensuring consistent styling across various UI components.
"""
from __future__ import annotations

import logging
from importlib import resources
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QStyle

from .. import config_manager
from . import styles

logger = logging.getLogger(__name__)


def themed_icon(name: str, fallback: QStyle.StandardPixmap) -> QIcon:
    """
    Returns a themed QIcon if available, otherwise falls back to a standard QStyle icon.

    This function attempts to load an icon by `name` from the current icon theme.
    If the themed icon is not found or is null, it retrieves a standard icon
    provided by Qt's current style.

    Args:
        name (str): The name of the icon to load from the current theme (e.g., "document-open").
        fallback (QStyle.StandardPixmap): A `QStyle.StandardPixmap` enum value to use
                                          if the themed icon is not available.

    Returns:
        QIcon: The loaded themed icon or the fallback standard icon.
    """
    icon = QIcon.fromTheme(name)
    if not icon.isNull():
        logger.debug(f"Loaded themed icon: {name}")
        return icon
    
    # Fallback to standard icon if themed icon is not found.
    style = QApplication.style()
    fallback_icon = style.standardIcon(fallback)
    logger.warning(f"Themed icon '{name}' not found. Falling back to standard icon: {fallback.name}")
    return fallback_icon


def resource_icon(name: str) -> QIcon:
    """
    Loads an icon from the bundled application resources folder.

    This function is designed to work with PyInstaller-bundled applications
    by using `importlib.resources` to access files within the package.

    Args:
        name (str): The filename of the icon (e.g., "clear.svg", "check-circle.svg").

    Returns:
        QIcon: A QIcon object loaded from the specified path. Returns an empty
               QIcon if the resource cannot be found or loaded, and logs an error.
    """
    try:
        # Construct the path to the icon within the package's resources.
        path = resources.files("mic_renamer.resources.icons") / name
        if path.is_file():
            logger.debug(f"Loading resource icon from: {path}")
            return QIcon(str(path))
        else:
            logger.warning(f"Resource icon file not found: {path}")
            return QIcon() # Return empty icon if file doesn't exist.
    except (ModuleNotFoundError, FileNotFoundError) as e:
        # Catch errors if the package or file is not found.
        logger.error(f"Failed to load resource icon '{name}' due to missing module/file: {e}")
        return QIcon()
    except Exception as e:
        # Catch any other unexpected errors during icon loading.
        logger.error(f"An unexpected error occurred while loading resource icon '{name}': {e}")
        return QIcon()


def apply_tag_box_style(app: QApplication) -> None:
    """
    Applies dynamic stylesheet rules specifically for the custom TagBox widgets.

    The styling adapts based on whether the current application theme is dark or light.
    It defines styles for normal, checked, and preselected states of the tag boxes.

    Args:
        app (QApplication): The QApplication instance to which the stylesheet will be applied.
    """
    is_dark = config_manager.get("theme", "dark") == "dark"
    logger.debug(f"Applying TagBox style for theme: {'dark' if is_dark else 'light'}")

    if is_dark:
        additional_style = """
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
        """
    else:
        # Light mode tag box styling
        additional_style = """
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
                color: #09090b;
                font-weight: bold;
            }
            /* checked state styling */
            *[class=\"tag-box-checked\"] QLabel#TagDesc,
            *[class=\"tag-box-checked\"] QLabel#TagCode {
                color: #ffffff;
            }
        """
    # Append the tag box specific styles to the application's current stylesheet.
    app.setStyleSheet(app.styleSheet() + additional_style)
    logger.debug("TagBox styles applied.")


def apply_styles(app: QApplication, theme: str = "dark") -> None:
    """
    Applies the overall visual theme (QSS stylesheet) to the application.

    This function sets the application's style to "Fusion" and then loads
    a theme-specific QSS file (dark_style.qss or shadcn_style.qss) from
    the bundled resources. Finally, it applies the custom TagBox styles.

    Args:
        app (QApplication): The QApplication instance to which the styles will be applied.
        theme (str): The name of the theme to apply ("dark" or "light"). Defaults to "dark".
    """
    app.setStyle("Fusion") # Set the application style to Fusion for a modern look.
    logger.info(f"Applying '{theme}' theme.")

    try:
        # Determine which QSS file to load based on the selected theme.
        if theme == "dark":
            qss_path = resources.files(styles) / "dark_style.qss"
        else:
            qss_path = resources.files(styles) / "shadcn_style.qss"

        # Read the content of the QSS file and apply it as the application's stylesheet.
        with qss_path.open("r", encoding="utf-8") as f: # Specify encoding for robustness
            app.setStyleSheet(f.read())
        logger.info(f"Loaded main stylesheet from: {qss_path}")

        # Apply additional styles specific to TagBox widgets.
        apply_tag_box_style(app)
        logger.info("All styles applied successfully.")
    except (FileNotFoundError, OSError) as e:
        # Log errors if the QSS file cannot be found or accessed.
        logger.error(f"Error applying main styles from {qss_path}: {e}. Application may not be themed correctly.")
        # Optionally, set a very basic fallback style here if critical.
    except Exception as e:
        # Catch any other unexpected errors during style application.
        logger.critical(f"An unexpected error occurred while applying styles: {e}")


