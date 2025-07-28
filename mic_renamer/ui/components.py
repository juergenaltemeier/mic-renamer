"""
This module contains custom UI components used in the mic-renamer application.
These components extend standard PySide6 widgets to provide enhanced functionality
and custom styling, such as drag-and-drop support for file lists and specialized
checkboxes for tags.
"""

from PySide6.QtWidgets import QListWidget, QListWidgetItem, QCheckBox, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox
from PySide6.QtCore import Qt, Signal
import os
import logging

from ..logic.settings import ItemSettings

logger = logging.getLogger(__name__)


class DragDropListWidget(QListWidget):
    """
    A custom QListWidget that supports drag-and-drop of files and folders.

    It filters dropped items to include only supported file extensions and prevents
    duplicate entries. When files are dropped, they are added to the list, and if
    the list was previously empty, the first added item is automatically selected.
    """

    def __init__(self):
        """
        Initializes the DragDropListWidget.
        Enables drag-and-drop and sets selection mode to single selection.
        """
        super().__init__()
        self.setAcceptDrops(True) # Enable drop events for this widget.
        self.setSelectionMode(QListWidget.SingleSelection) # Allow only one item to be selected at a time.
        self.setMinimumWidth(300) # Set a minimum width for the widget.
        logger.debug("DragDropListWidget initialized.")

    def dragEnterEvent(self, event) -> None:
        """
        Handles drag enter events.

        Accepts the proposed action if the dragged data contains URLs (file paths).

        Args:
            event (QDragEnterEvent): The drag enter event.
        """
        if event.mimeData().hasUrls():
            event.acceptProposedAction() # Accept the drag if it contains file URLs.
            logger.debug("Drag enter event accepted (has URLs).")
        else:
            super().dragEnterEvent(event) # Pass to base class if not file URLs.
            logger.debug("Drag enter event ignored (no URLs).")

    def dragMoveEvent(self, event) -> None:
        """
        Handles drag move events.

        Accepts the proposed action if the dragged data contains URLs.

        Args:
            event (QDragMoveEvent): The drag move event.
        """
        if event.mimeData().hasUrls():
            event.acceptProposedAction() # Accept the drag move if it contains file URLs.
            logger.debug("Drag move event accepted (has URLs).")
        else:
            super().dragMoveEvent(event) # Pass to base class if not file URLs.
            logger.debug("Drag move event ignored (no URLs).")

    def dropEvent(self, event) -> None:
        """
        Handles drop events, processing dropped file URLs.

        Adds supported files to the list, avoiding duplicates, and sets the first
        newly added item as current if no item was selected previously.

        Args:
            event (QDropEvent): The drop event.
        """
        if event.mimeData().hasUrls():
            added_any_file = False
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                logger.debug(f"Dropped item: {path}")
                if os.path.isfile(path):
                    ext = os.path.splitext(path)[1].lower()
                    # Check if the file extension is among the accepted types.
                    if ext in ItemSettings.ACCEPT_EXTENSIONS:
                        # Check for duplicates to prevent adding the same file multiple times.
                        is_duplicate = False
                        for i in range(self.count()):
                            if self.item(i).data(Qt.UserRole) == path:
                                is_duplicate = True
                                logger.info(f"Skipping duplicate file: {path}")
                                break
                        
                        if not is_duplicate:
                            # Create a new QListWidgetItem with the base filename.
                            item = QListWidgetItem(os.path.basename(path))
                            # Store the full original path in UserRole for later retrieval.
                            item.setData(Qt.UserRole, path)
                            # Initialize ItemSettings data to None; it will be populated later in main_window.
                            item.setData(Qt.UserRole + 1, None) 
                            self.addItem(item)
                            added_any_file = True
                            logger.info(f"Added file to list: {path}")
                    else:
                        logger.warning(f"Dropped file has unsupported extension: {path}")
                else:
                    logger.debug(f"Dropped item is not a file or is a directory: {path}. Directories are handled elsewhere.")
            
            # If any new files were added and no item was previously selected, select the first item.
            if added_any_file and self.currentItem() is None and self.count() > 0:
                self.setCurrentRow(0)
                logger.debug("Automatically selected the first added item.")
            event.acceptProposedAction() # Accept the drop action.
        else:
            super().dropEvent(event) # Pass to base class if not file URLs.
            logger.debug("Drop event ignored (no URLs).")


class EnterToggleCheckBox(QCheckBox):
    """
    A custom QCheckBox that toggles its state when the Return or Enter key is pressed.

    This provides an alternative way to interact with the checkbox using keyboard input.
    """

    def keyPressEvent(self, event) -> None:
        """
        Handles key press events for the checkbox.

        If the pressed key is Return or Enter, it toggles the checkbox state.
        Otherwise, it passes the event to the base class.

        Args:
            event (QKeyEvent): The key press event.
        """
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.toggle() # Toggle the checkbox state.
            event.accept() # Mark the event as handled.
            logger.debug(f"EnterToggleCheckBox toggled by key press: {self.text()}, new state: {self.isChecked()}")
        else:
            super().keyPressEvent(event) # Pass the event to the parent class.


class TagBox(EnterToggleCheckBox):
    """
    A custom checkbox designed to display a tag with its code and description.

    It extends `EnterToggleCheckBox` and provides custom styling based on its
    checked state and whether it's preselected.
    """
    def __init__(self, code: str, description: str, parent=None):
        """
        Initializes a TagBox.

        Args:
            code (str): The short code for the tag (e.g., "AU").
            description (str): A longer description of the tag (e.g., "Autoclave").
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.code = code
        self.description = description
        self._preselected = False # Internal flag for preselected state.

        # Set the display text (code on first line, description on second) and tooltip.
        self.setText(f"{code.upper()}\n{description}")
        self.setToolTip(f"{code}: {description}")
        
        # Connect the toggled signal to update the style dynamically.
        self.toggled.connect(self._update_style)
        # Apply initial style based on current checked state.
        self._update_style(self.isChecked())
        logger.debug(f"TagBox initialized for tag: {code}")

    def set_text(self, code: str, description: str) -> None:
        """
        Updates the code and description displayed by the TagBox.

        Args:
            code (str): The new short code for the tag.
            description (str): The new longer description of the tag.
        """
        self.code = code
        self.description = description
        self.setText(f"{code.upper()}\n{description}")
        self.setToolTip(f"{code}: {description}")
        logger.debug(f"TagBox text updated to: {code} - {description}")

    def set_preselected(self, preselected: bool) -> None:
        """
        Sets the preselected state of the TagBox.

        A preselected tag might have a different visual style. This method triggers
        a style update if the preselected state changes.

        Args:
            preselected (bool): True if the tag should be marked as preselected, False otherwise.
        """
        if self._preselected != preselected:
            self._preselected = preselected
            self._update_style(self.isChecked()) # Update style based on new preselected state.
            logger.debug(f"TagBox '{self.code}' preselected state set to: {preselected}")

    def _update_style(self, checked: bool) -> None:
        """
        Internal method to update the visual style of the TagBox based on its state.

        This method applies different CSS classes based on whether the checkbox is
        checked, preselected, or neither. It then unpolishes and polishes the widget
        to force a style recalculation.

        Args:
            checked (bool): The current checked state of the checkbox.
        """
        if self._preselected:
            self.setProperty("class", "tag-box-preselected")
            logger.debug(f"TagBox '{self.code}' style set to tag-box-preselected.")
        elif checked:
            self.setProperty("class", "tag-box-checked")
            logger.debug(f"TagBox '{self.code}' style set to tag-box-checked.")
        else:
            self.setProperty("class", "tag-box")
            logger.debug(f"TagBox '{self.code}' style set to tag-box.")
        
        # Force style recalculation.
        self.style().unpolish(self)
        self.style().polish(self)

    def setChecked(self, checked: bool) -> None:
        """
        Overrides the base `setChecked` method to ensure visual style updates.

        This ensures that the `_update_style` method is called even when the
        `toggled` signal might be blocked, guaranteeing consistent visual feedback.

        Args:
            checked (bool): The new checked state for the checkbox.
        """
        super().setChecked(checked)
        self._update_style(self.isChecked()) # Explicitly call style update.
        logger.debug(f"TagBox '{self.code}' checked state set to: {checked}")

