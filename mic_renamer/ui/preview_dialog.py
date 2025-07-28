"""
This module defines the `PreviewDialog` class, a PyQt/PySide dialog that displays
a preview of file renaming operations. It allows users to review the proposed
new file names before committing to the changes.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, List, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets (
    QDialog,
    QDialogButtonBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ..utils.i18n import tr

# Type checking for ItemSettings to avoid circular imports if needed
if TYPE_CHECKING:
    from ..logic.settings import ItemSettings

logger = logging.getLogger(__name__)


class PreviewDialog(QDialog):
    """
    A dialog that displays a preview of the file renaming operations.

    It presents a table showing the current file names and their proposed new names,
    allowing the user to review the changes before confirmation.
    """

    def __init__(self, parent, mapping: List[Tuple['ItemSettings', str, str]]):
        """
        Initializes the PreviewDialog.

        Args:
            parent (QWidget): The parent widget for this dialog.
            mapping (List[Tuple[ItemSettings, str, str]]): A list of tuples, where each tuple contains:
                                                            - An `ItemSettings` object (though only paths are used here).
                                                            - The original absolute file path (str).
                                                            - The proposed new absolute file path (str).
        """
        super().__init__(parent)
        self.setWindowTitle(tr("preview_rename")) # Set dialog title from translations.
        logger.info("PreviewDialog initialized.")
        self._setup_ui(mapping) # Set up the user interface.

    def _setup_ui(self, mapping: List[Tuple['ItemSettings', str, str]]) -> None:
        """
        Sets up the user interface of the dialog.

        This includes creating the main vertical layout, the preview table,
        and the standard OK/Cancel button box.

        Args:
            mapping (List[Tuple[ItemSettings, str, str]]): The mapping data to populate the table.
        """
        layout = QVBoxLayout(self) # Main vertical layout for the dialog.
        
        self.table = self._create_table(mapping) # Create and populate the table widget.
        layout.addWidget(self.table) # Add the table to the layout.

        # Create standard OK and Cancel buttons.
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept) # Connect OK button to dialog's accept slot.
        btns.rejected.connect(self.reject) # Connect Cancel button to dialog's reject slot.
        layout.addWidget(btns) # Add buttons to the layout.
        logger.debug("PreviewDialog UI setup complete.")

    def _create_table(self, mapping: List[Tuple['ItemSettings', str, str]]) -> QTableWidget:
        """
        Creates and populates the QTableWidget used for displaying the rename preview.

        The table has two columns: "Current Name" and "Proposed New Name".
        It is configured to be read-only and non-selectable.

        Args:
            mapping (List[Tuple[ItemSettings, str, str]]): The data containing original and new paths.

        Returns:
            QTableWidget: The configured and populated table widget.
        """
        # Initialize table with number of rows equal to mapping length and 2 columns.
        table = QTableWidget(len(mapping), 2)
        # Set horizontal header labels using translated strings.
        table.setHorizontalHeaderLabels([
            tr("current_name"),
            tr("proposed_new_name")
        ])
        table.verticalHeader().setVisible(False) # Hide row numbers.
        table.setEditTriggers(QTableWidget.NoEditTriggers) # Make table cells read-only.
        table.setSelectionMode(QTableWidget.NoSelection) # Disable selection.
        table.setFocusPolicy(Qt.NoFocus) # Prevent table from taking focus.
        logger.debug(f"Preview table created with {len(mapping)} rows.")

        # Populate the table with data from the mapping.
        for row_idx, (item_setting, orig_path_str, new_path_str) in enumerate(mapping):
            # Extract just the filename from the full paths for display.
            current_name = Path(orig_path_str).name
            proposed_name = Path(new_path_str).name
            
            # Create QTableWidgetItem for current name and set it.
            table.setItem(row_idx, 0, QTableWidgetItem(current_name))
            # Create QTableWidgetItem for proposed new name and set it.
            table.setItem(row_idx, 1, QTableWidgetItem(proposed_name))
            logger.debug(f"Table row {row_idx}: '{current_name}' -> '{proposed_name}'")

        # Adjust column widths to fit content.
        table.resizeColumnsToContents()
        table.resizeRowsToContents()
        table.setMinimumWidth(600) # Ensure a minimum width for readability.
        logger.debug("Preview table populated and resized.")
        return table


def show_preview(parent, mapping: list[tuple]) -> bool:
    """
    Convenience function to create, show, and execute the PreviewDialog.

    Args:
        parent (QWidget): The parent widget for the dialog.
        mapping (list[tuple]): The list of rename mappings to display.
                               Expected format: list of (ItemSettings, original_path_str, new_path_str).

    Returns:
        bool: True if the user accepts the preview (clicks OK), False otherwise (clicks Cancel or closes dialog).
    """
    logger.info("Showing rename preview dialog.")
    dlg = PreviewDialog(parent, mapping)
    # Execute the dialog modally and return its result.
    result = dlg.exec() == QDialog.Accepted
    logger.info(f"Preview dialog closed. Accepted: {result}")
    return result
