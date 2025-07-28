"""
This module defines the `WrapToolBar` class, a custom QWidget that functions as a toolbar
but uses a `FlowLayout` to automatically wrap its contents (buttons, widgets, separators)
to multiple lines when horizontal space is limited. This provides a more flexible and
responsive toolbar layout compared to standard QToolBar.
"""
from __future__ import annotations

import logging
from typing import Iterable, List

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QFrame, QToolButton, QWidget

from .constants import DEFAULT_MARGIN, DEFAULT_SPACING
from .flow_layout import FlowLayout

logger = logging.getLogger(__name__)


class WrapToolBar(QWidget):
    """
    A toolbar-like widget that arranges its buttons and other widgets horizontally
    and wraps them to new rows when the available width is exceeded.

    It provides methods similar to QToolBar for adding actions, widgets, and separators,
    while offering flexible layout behavior.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initializes the WrapToolBar.

        Args:
            parent (QWidget | None): The parent widget of this toolbar. Defaults to None.
        """
        super().__init__(parent)
        # Use FlowLayout as the internal layout manager.
        self._layout = FlowLayout(self)
        # Set margins and spacing for the internal FlowLayout.
        self._layout.setContentsMargins(
            DEFAULT_MARGIN, DEFAULT_MARGIN, DEFAULT_MARGIN, DEFAULT_MARGIN
        )
        self._layout.setSpacing(DEFAULT_SPACING)
        
        self._buttons: List[QToolButton] = [] # List to keep track of all QToolButtons added.
        self._tool_button_style = Qt.ToolButtonIconOnly # Default style for tool buttons.
        self._icon_size = QSize(24, 24) # Default icon size.
        logger.info("WrapToolBar initialized.")

    def addAction(self, action: QAction) -> QToolButton:
        """
        Adds a QAction to the toolbar, creating a QToolButton for it.

        The created button will automatically reflect the action's properties
        (icon, text, enabled state, tooltip) and will be styled according to
        the toolbar's current button style and icon size.

        Args:
            action (QAction): The QAction to add to the toolbar.

        Returns:
            QToolButton: The newly created QToolButton associated with the action.
        """
        btn = QToolButton() # Create a new tool button.
        btn.setDefaultAction(action) # Associate the action with the button.
        btn.setToolButtonStyle(self._tool_button_style) # Apply current button style.
        btn.setIconSize(self._icon_size) # Apply current icon size.
        self._layout.addWidget(btn) # Add the button to the flow layout.
        self._buttons.append(btn) # Keep a reference to the button.
        logger.debug(f"Action '{action.text()}' added to WrapToolBar.")
        return btn

    def addWidget(self, widget: QWidget) -> None:
        """
        Adds an arbitrary QWidget to the toolbar.

        If the added widget is a QToolButton, its style and icon size will be
        set to match the toolbar's current settings.

        Args:
            widget (QWidget): The widget to add to the toolbar.
        """
        self._layout.addWidget(widget) # Add the widget to the flow layout.
        if isinstance(widget, QToolButton):
            # If it's a QToolButton, apply the toolbar's styling.
            widget.setToolButtonStyle(self._tool_button_style)
            widget.setIconSize(self._icon_size)
            self._buttons.append(widget) # Also keep a reference if it's a tool button.
            logger.debug(f"QToolButton '{widget.objectName() or widget.text()}' added to WrapToolBar.")
        else:
            logger.debug(f"Widget '{widget.objectName()}' added to WrapToolBar.")

    def addSeparator(self) -> None:
        """
        Adds a vertical separator line to the toolbar.

        This creates a `QFrame` configured as a vertical line to visually separate
        groups of items in the toolbar.
        """
        line = QFrame() # Create a QFrame.
        line.setFrameShape(QFrame.VLine) # Set its shape to a vertical line.
        line.setFrameShadow(QFrame.Sunken) # Give it a sunken 3D effect.
        self._layout.addWidget(line) # Add the separator to the layout.
        logger.debug("Separator added to WrapToolBar.")

    def actions(self) -> Iterable[QAction]:
        """
        Returns an iterable of all QAction objects currently associated with buttons in the toolbar.

        Returns:
            Iterable[QAction]: An iterable containing QAction instances.
        """
        # Filter out buttons that might not have a default action (e.g., if a plain widget was added).
        return (
            btn.defaultAction() for btn in self._buttons if btn.defaultAction() is not None
        )

    def setToolButtonStyle(self, style: Qt.ToolButtonStyle) -> None:
        """
        Sets the tool button style for all existing and future buttons in the toolbar.

        This controls how icons and text are displayed on the buttons (e.g., icon only, text only, text beside icon).

        Args:
            style (Qt.ToolButtonStyle): The desired style for the tool buttons.
        """
        self._tool_button_style = style # Store the new style.
        for btn in self._buttons:
            btn.setToolButtonStyle(style) # Apply the style to all existing buttons.
        logger.info(f"Tool button style set to: {style.name}")

    def toolButtonStyle(self) -> Qt.ToolButtonStyle:
        """
        Returns the current tool button style applied to the toolbar.

        Returns:
            Qt.ToolButtonStyle: The current style.
        """
        return self._tool_button_style

    def setIconSize(self, size: QSize) -> None:
        """
        Sets the icon size for all existing and future buttons in the toolbar.

        Args:
            size (QSize): The desired size for icons (width and height).
        """
        self._icon_size = size # Store the new icon size.
        for btn in self._buttons:
            btn.setIconSize(size) # Apply the size to all existing buttons.
        logger.info(f"Icon size set to: {size.width()}x{size.height()}")

    def iconSize(self) -> QSize:
        """
        Returns the current icon size applied to the toolbar.

        Returns:
            QSize: The current icon size.
        """
        return self._icon_size

