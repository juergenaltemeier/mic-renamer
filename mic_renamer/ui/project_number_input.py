"""
This module defines the `ProjectNumberInput` widget, a custom UI component for
inputting project numbers in a specific format (e.g., "C123456"). It provides
real-time validation, a clear button, and integrates with the application's
icon resources.
"""
from __future__ import annotations

import logging
import re
import sys
from importlib import resources
from pathlib import Path

from PySide6.QtCore import QRegularExpression, Qt, Signal, QObject
from PySide6.QtGui import QIcon, QRegularExpressionValidator, QKeyEvent
from PySide6.QtWidgets (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QToolButton,
    QWidget,
)

from .constants import DEFAULT_SPACING
from .theme import resource_icon # Assuming resource_icon is also defined in theme.py

logger = logging.getLogger(__name__)


class ProjectNumberInput(QWidget):
    """
    A custom input widget for project numbers, typically in the format "C123456".

    This widget combines a fixed prefix label ("C"), a QLineEdit for the numeric part,
    a validation indicator, and a clear button. It enforces a 6-digit numeric input
    and provides visual feedback on validity.
    """

    # Signal emitted when the text in the input field changes.
    textChanged = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initializes the ProjectNumberInput widget.

        Args:
            parent (QWidget | None): The parent widget of this input. Defaults to None.
        """
        super().__init__(parent)
        logger.info("ProjectNumberInput widget initialized.")
        self._setup_ui() # Build the UI components.

    def _setup_ui(self) -> None:
        """
        Creates and arranges all the UI components within the ProjectNumberInput widget.

        This includes the main horizontal layout, the 'C' prefix label, the QLineEdit
        for the numeric input, a validation label, and a clear button.
        """
        # Main horizontal layout for the widget, with no margins.
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(DEFAULT_SPACING) # Use default spacing between elements.

        # 'C' prefix label.
        self.prefix_label = QLabel("C")
        layout.addWidget(self.prefix_label)

        # QLineEdit for the 6-digit project number.
        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText("123456") # Placeholder text for user guidance.
        self.line_edit.setMinimumWidth(100) # Ensure a reasonable minimum width.
        # Connect text changes to a handler for validation and signal emission.
        self.line_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.line_edit)

        # Label to display validation status (e.g., checkmark or empty).
        self.validation_label = QLabel()
        layout.addWidget(self.validation_label)

        # Clear button to reset the input.
        self.btn_clear = QToolButton()
        self.btn_clear.setIcon(resource_icon("clear.svg")) # Load clear icon.
        self.btn_clear.setToolTip("Clear") # Tooltip for the button.
        self.btn_clear.setCursor(Qt.ArrowCursor) # Set cursor to arrow.
        self.btn_clear.clicked.connect(self.clear) # Connect to clear method.
        self.btn_clear.hide() # Initially hide the clear button.
        layout.addWidget(self.btn_clear)

        # Validator to restrict input to 0-6 digits.
        # This prevents non-digit characters from being entered.
        self.validator = QRegularExpressionValidator(QRegularExpression(r"\d{0,6}"))
        self.line_edit.setValidator(self.validator)

        # Set the line edit as the focus proxy, so focusing the widget focuses the line edit.
        self.setFocusProxy(self.line_edit)
        logger.debug("ProjectNumberInput UI setup complete.")

    def _on_text_changed(self, text: str) -> None:
        """
        Handles the `textChanged` signal from the internal QLineEdit.

        This method updates the visibility of the clear button, triggers input
        validation, and emits the `textChanged` signal with the full project code.

        Args:
            text (str): The current text in the QLineEdit (the numeric part).
        """
        # Show the clear button only if there is text in the input field.
        self.btn_clear.setVisible(bool(text))
        self.validate_input() # Perform validation and update the icon.
        self.textChanged.emit(self.text()) # Emit the signal with the full project code.
        logger.debug(f"Project number text changed to: {self.text()}")

    def validate_input(self) -> bool:
        """
        Validates the current input in the QLineEdit and updates the validation label.

        A project number is considered valid if it consists of exactly 6 digits.

        Returns:
            bool: True if the input is valid (6 digits), False otherwise.
        """
        text = self.line_edit.text()
        # Check if the text has exactly 6 digits.
        is_valid = len(text) == 6 and text.isdigit()

        if is_valid:
            # If valid, display a checkmark icon.
            self.validation_label.setPixmap(
                resource_icon("check-circle.svg").pixmap(16, 16)
            )
            logger.debug(f"Project number '{self.text()}' is valid.")
        else:
            # If invalid, clear any existing pixmap.
            self.validation_label.setPixmap(QIcon().pixmap(16, 16)) # Set an empty pixmap
            logger.debug(f"Project number '{self.text()}' is invalid.")

        return is_valid

    def text(self) -> str:
        """
        Returns the full project code, including the 'C' prefix.

        Returns:
            str: The complete project code (e.g., "C123456").
        """
        full_text = f"C{self.line_edit.text()}"
        return full_text

    def setText(self, text: str) -> None:
        """
        Sets the text of the project number input widget.

        This method handles stripping the 'C' prefix if present and sets the
        numeric part to the QLineEdit.

        Args:
            text (str): The project code string to set (e.g., "C123456" or "123456").
        """
        # Remove 'C' prefix if present, to set only the numeric part to the QLineEdit.
        if text.upper().startswith("C"):
            text = text[1:]
        self.line_edit.setText(text) # Set the text in the QLineEdit.
        logger.debug(f"Project number text set to: {self.text()}")

    def clear(self) -> None:
        """
        Clears the input field of the project number.

        This resets the numeric part of the project code to empty.
        """
        self.line_edit.clear() # Clear the text in the QLineEdit.
        logger.info("Project number input cleared.")

