"""
This module defines the `OtpInput` widget, a custom UI component designed for
inputting a 6-digit project code (e.g., "C123456"). It features individual
QLineEdit fields for each digit, automatic tabbing, validation feedback, and
a clear button. It also includes a helper function for loading icons.
"""
from __future__ import annotations

import re
import sys
import logging
from importlib import resources
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QIcon, QKeyEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QWidget,
)

logger = logging.getLogger(__name__)


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
            logger.debug(f"Loading icon from: {path}")
            return QIcon(str(path))
        else:
            logger.warning(f"Icon file not found: {path}")
            return QIcon() # Return empty icon if file doesn't exist.
    except (ModuleNotFoundError, FileNotFoundError) as e:
        # Catch errors if the package or file is not found.
        logger.error(f"Failed to load icon '{name}' due to missing module/file: {e}")
        return QIcon()
    except Exception as e:
        # Catch any other unexpected errors during icon loading.
        logger.error(f"An unexpected error occurred while loading icon '{name}': {e}")
        return QIcon()


class OtpInput(QWidget):
    """
    A custom widget for inputting a 6-digit project code in an OTP (One-Time Password) style.

    This widget comprises a prefix label ("C"), six individual QLineEdit fields for digits,
    a validation icon, and a clear button. It provides enhanced user experience through
    automatic focus shifting, keyboard navigation, and real-time validation feedback.
    """

    # Signal emitted when the full text of the input changes.
    textChanged = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        """
        Initializes the OtpInput widget.

        Args:
            parent (QWidget | None): The parent widget of this custom input. Defaults to None.
        """
        super().__init__(parent)
        # Set size policy to fixed width and preferred height, allowing it to take up minimal horizontal space.
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.setObjectName("OtpInput") # Set object name for QSS styling.
        logger.info("OtpInput widget initialized.")

        self._setup_ui() # Build the UI components.
        self._apply_styles() # Apply custom CSS styles.

    def _setup_ui(self) -> None:
        """
        Creates and arranges all the UI components within the OtpInput widget.

        This includes the main container layout, a frame for visual grouping,
        the 'C' prefix label, six individual QLineEdit fields, a validation label,
        and a clear button.
        """
        # Main layout for the widget, with no margins or spacing.
        container_layout = QHBoxLayout(self)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # A QFrame to visually group the input fields and apply a border.
        frame = QFrame(self)
        frame.setObjectName("OtpFrame") # Object name for QSS.
        container_layout.addWidget(frame)
        container_layout.setAlignment(frame, Qt.AlignVCenter) # Center the frame vertically.

        # Layout within the frame for the input elements.
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(6, 2, 6, 2) # Internal margins for the frame's content.
        layout.setSpacing(8) # Spacing between input fields.

        # 'C' prefix label.
        self.prefix_label = QLabel("C", self)
        self.prefix_label.setObjectName("OtpPrefix")
        self.prefix_label.setFixedSize(20, 20) # Fixed size for consistent appearance.
        self.prefix_label.setAlignment(Qt.AlignCenter) # Center text.
        layout.addWidget(self.prefix_label)

        # Create 6 individual QLineEdit fields for digit input.
        self.line_edits: list[QLineEdit] = []
        for i in range(6):
            line_edit = QLineEdit(self)
            line_edit.setObjectName("OtpLineEdit")
            line_edit.setMaxLength(1) # Allow only one character per field.
            line_edit.setFixedSize(25, 25) # Fixed size for each input box.
            line_edit.setAlignment(Qt.AlignCenter) # Center text.
            # Connect text changes to a handler for auto-tabbing and validation.
            line_edit.textChanged.connect(self._on_text_changed)
            # Install an event filter to handle Backspace, Left, Right arrow keys.
            line_edit.installEventFilter(self)
            self.line_edits.append(line_edit)
            layout.addWidget(line_edit)
        logger.debug("Created 6 QLineEdit fields for OTP input.")

        # Label to display validation status (e.g., checkmark).
        self.validation_label = QLabel(self)
        self.validation_label.setFixedSize(20, 20)
        self.validation_label.setScaledContents(True) # Scale pixmap to fit label size.
        layout.addWidget(self.validation_label)

        # Button to clear all input fields.
        self.clear_button = QPushButton(self)
        self.clear_button.setObjectName("OtpClearButton")
        self.clear_button.setIcon(resource_icon("clear.svg")) # Load clear icon.
        self.clear_button.setFixedSize(20, 20)
        self.clear_button.setFlat(True) # Make it look like a tool button.
        self.clear_button.clicked.connect(self.clear) # Connect to clear method.
        layout.addWidget(self.clear_button)
        logger.debug("OtpInput UI setup complete.")

    def _apply_styles(self) -> None:
        """
        Applies custom CSS (QSS) styles to the OtpInput widget and its child components.

        This method defines the visual appearance of the input fields, frame,
        prefix label, and clear button.
        """
        self.setStyleSheet(
            """
            #OtpFrame {
                border: 1px solid palette(midlight);
                border-radius: 6px;
            }
            #OtpPrefix {
                font-weight: bold;
                font-size: 14px;
            }
            QLineEdit#OtpLineEdit {
                border: 1px solid palette(midlight);
                border-radius: 3px;
                qproperty-alignment: 'AlignCenter';
            }
            QLineEdit#OtpLineEdit:focus {
                border: 1px solid palette(highlight);
            }
            #OtpClearButton {
                border: none;
            }
            #OtpClearButton:pressed {
                background-color: palette(midlight);
            }
        """
        )
        # Set maximum width based on the calculated size hint to prevent excessive horizontal expansion.
        self.setMaximumWidth(self.sizeHint().width())
        logger.debug("OtpInput styles applied.")

    def _on_text_changed(self, text: str) -> None:
        """
        Handles the `textChanged` signal from individual QLineEdit fields.

        This method implements the auto-tabbing logic: when a digit is entered
        into a field, focus automatically shifts to the next field. It also
        handles pasting multi-digit text and triggers validation.

        Args:
            text (str): The new text in the QLineEdit that emitted the signal.
        """
        sender = self.sender()
        # Ensure the sender is a QLineEdit to prevent unexpected behavior.
        if not isinstance(sender, QLineEdit):
            logger.warning(f"_on_text_changed called by non-QLineEdit object: {type(sender)}")
            return

        # If more than one character is pasted into a single field, distribute it.
        if len(text) > 1:
            logger.debug(f"Multi-character input detected: '{text}'. Distributing.")
            self.setText(text) # Call setText to distribute the characters across fields.
            return

        try:
            current_index = self.line_edits.index(sender)
        except ValueError:
            logger.error(f"Sender {sender} not found in line_edits list.")
            return

        # If a single character is entered and it's not the last field, move focus to the next.
        if len(text) == 1 and current_index < len(self.line_edits) - 1:
            next_field = self.line_edits[current_index + 1]
            next_field.setFocus() # Move focus.
            next_field.selectAll() # Select text in the next field for easy overwriting.
            logger.debug(f"Auto-tabbed from field {current_index} to {current_index + 1}.")

        # Get the full text from all fields and emit the signal.
        full_text = self.text()
        self.textChanged.emit(full_text)
        # Update the validation icon based on the new full text.
        self.update_validation_status(full_text)

    def eventFilter(self, obj: QObject, event: QKeyEvent) -> bool:
        """
        Filters events for the individual QLineEdit fields to handle keyboard navigation.

        This enables Backspace to move to the previous field and delete content,
        and Left/Right arrow keys to navigate between fields.

        Args:
            obj (QObject): The object that received the event (expected to be a QLineEdit).
            event (QKeyEvent): The key event that occurred.

        Returns:
            bool: True if the event was handled and should not be propagated further,
                  False otherwise.
        """
        # Only process KeyPress events for our line edits.
        if event.type() == QKeyEvent.KeyPress and obj in self.line_edits:
            key = event.key()
            current_index = self.line_edits.index(obj)

            # Handle Backspace: if current field is empty, move to previous field and select its content.
            if key == Qt.Key_Backspace and not obj.text() and current_index > 0:
                prev_field = self.line_edits[current_index - 1]
                prev_field.setFocus()
                prev_field.selectAll()
                logger.debug(f"Backspace: Moved focus from {current_index} to {current_index - 1}.")
                return True # Event handled.
            # Handle Left arrow key: move focus to previous field.
            elif key == Qt.Key_Left and current_index > 0:
                self.line_edits[current_index - 1].setFocus()
                self.line_edits[current_index - 1].selectAll()
                logger.debug(f"Left arrow: Moved focus from {current_index} to {current_index - 1}.")
                return True # Event handled.
            # Handle Right arrow key: move focus to next field.
            elif key == Qt.Key_Right and current_index < len(self.line_edits) - 1:
                self.line_edits[current_index + 1].setFocus()
                self.line_edits[current_index + 1].selectAll()
                logger.debug(f"Right arrow: Moved focus from {current_index} to {current_index + 1}.")
                return True # Event handled.

        # For other events or if not one of our line edits, pass to the base class.
        return super().eventFilter(obj, event)

    def text(self) -> str:
        """
        Retrieves the full project code string from all individual input fields.

        The project code is always prefixed with 'C'.

        Returns:
            str: The complete project code (e.g., "C123456").
        """
        # Concatenate the text from all line edits and prepend 'C'.
        full_text = "C" + "".join([le.text() for le in self.line_edits])
        logger.debug(f"Current full text: {full_text}")
        return full_text

    def setText(self, text: str) -> None:
        """
        Sets the text of the OTP input widget, distributing characters across fields.

        This method handles setting the project code programmatically. It also
        manages the focus after setting the text and triggers validation.

        Args:
            text (str): The project code string to set (e.g., "C123456" or "123456").
        """
        # Block signals from line edits to prevent multiple `_on_text_changed` calls during programmatic update.
        for le in self.line_edits:
            le.blockSignals(True)

        # Remove 'C' prefix if present, to get only the digits.
        if text and text.upper().startswith("C"):
            text = text[1:]
        
        # Distribute characters to individual line edits.
        for i, line_edit in enumerate(self.line_edits):
            if i < len(text):
                line_edit.setText(text[i])
            else:
                line_edit.clear() # Clear remaining fields if input text is shorter.
        logger.debug(f"Text set to: {text}")

        # Unblock signals after setting text.
        for le in self.line_edits:
            le.blockSignals(False)

        # Get the full text after update and emit signal.
        full_text = self.text()
        self.textChanged.emit(full_text)
        # Update validation status.
        self.update_validation_status(full_text)

        # Set focus to the last filled field or the first field if cleared.
        if text:
            last_filled_index = min(len(text) - 1, len(self.line_edits) - 1)
            self.line_edits[last_filled_index].setFocus()
            self.line_edits[last_filled_index].selectAll()
            logger.debug(f"Focus set to field {last_filled_index}.")
        else:
            self.line_edits[0].setFocus()
            logger.debug("Focus set to first field after clearing.")

    def clear(self) -> None:
        """
        Clears all input fields in the widget.

        Resets the text to empty, clears the validation status, and sets focus
        back to the first input field.
        """
        for le in self.line_edits:
            le.clear() # Clear text in each line edit.
        self.line_edits[0].setFocus() # Set focus to the first field.
        self.textChanged.emit(self.text()) # Emit textChanged signal with empty text.
        self.update_validation_status(self.text()) # Update validation status (should clear icon).
        logger.info("OtpInput fields cleared.")

    def update_validation_status(self, text: str) -> None:
        """
        Updates the validation icon displayed next to the input fields.

        If the provided `text` matches the expected format (C followed by 6 digits),
        a success icon is shown. Otherwise, the validation icon is cleared.

        Args:
            text (str): The full project code string to validate.
        """
        # Use a regular expression to validate the format: 'C' followed by exactly 6 digits.
        if re.fullmatch(r"C\d{6}", text):
            # If valid, set the check-circle icon.
            self.validation_label.setPixmap(resource_icon("check-circle.svg").pixmap(20, 20))
            logger.debug(f"Validation status: Valid for '{text}'.")
        else:
            # If invalid, clear any existing pixmap.
            self.validation_label.clear()
            logger.debug(f"Validation status: Invalid for '{text}'.")


# Example usage when run as a standalone script.
if __name__ == "__main__":
    # Create a QApplication instance.
    app = QApplication(sys.argv)
    # Apply a simple stylesheet for demonstration.
    app.setStyleSheet("QWidget { background-color: #F0F0F0; }")
    
    # Create an instance of the OtpInput widget.
    widget = OtpInput()
    widget.setWindowTitle("OTP Input Example")
    widget.resize(300, 100)
    widget.show() # Display the widget.
    
    # Start the Qt event loop.
    sys.exit(app.exec())
