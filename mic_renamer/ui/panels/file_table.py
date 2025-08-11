"""Table widget with drag and drop support."""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Set, Tuple

import logging
import os
from PySide6.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QMenu,
    QInputDialog,
    QMessageBox,
    QStyledItemDelegate,
    QLineEdit,
)
from PySide6.QtGui import QAction, QDesktopServices, QKeyEvent
from PySide6.QtCore import (
    Qt,
    QTimer,
    QItemSelection,
    QEvent,
    Signal,
    QUrl,
    QObject,
)

from ...logic.settings import ItemSettings
from ...logic.tag_loader import load_tags
from ...logic.tag_service import extract_tags_from_name, extract_suffix_from_name
from ...logic.heic_converter import convert_heic
from ...utils.i18n import tr
from ...utils.meta_utils import get_capture_date

# Type checking for ItemSettings to avoid circular imports if needed
if TYPE_CHECKING:
    from ...logic.settings import ItemSettings

ROLE_SETTINGS = Qt.UserRole + 1 # Custom Qt.ItemDataRole for storing ItemSettings objects.
logger = logging.getLogger(__name__)


class CustomDelegate(QStyledItemDelegate):
    """
    A custom item delegate for QTableWidget that provides a context menu for QLineEdit editors.

    This allows right-clicking within an editable cell to bring up the table's context menu,
    which is useful for actions like adding/removing tags or suffixes.
    """
    def createEditor(self, parent: QWidget, option: 'QStyleOptionViewItem', index: 'QModelIndex') -> QWidget:
        """
        Creates and returns the editor widget for the specified index.

        If the editor is a QLineEdit, it installs a custom context menu policy.

        Args:
            parent (QWidget): The parent widget for the editor.
            option (QStyleOptionViewItem): The style options for the item.
            index (QModelIndex): The model index of the item being edited.

        Returns:
            QWidget: The editor widget.
        """
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            editor.setContextMenuPolicy(Qt.CustomContextMenu) # Enable custom context menu.
            # Connect the custom context menu request signal to our handler.
            editor.customContextMenuRequested.connect(self.show_editor_context_menu)
            logger.debug(f"Created QLineEdit editor for index {index.row()},{index.column()} with custom context menu.")
        return editor

    def show_editor_context_menu(self, pos: 'QPoint') -> None:
        """
        Displays the table's context menu when requested from an editor (QLineEdit).

        Args:
            pos (QPoint): The position where the context menu was requested (local to the editor).
        """
        editor = self.sender()
        if not isinstance(editor, QLineEdit):
            logger.warning("show_editor_context_menu called by non-QLineEdit sender.")
            return

        table = self.parent()
        if not isinstance(table, DragDropTableWidget):
            logger.error("Delegate's parent is not DragDropTableWidget. Cannot show context menu.")
            return

        menu = table._create_context_menu() # Get the table's context menu.
        menu.exec_(editor.mapToGlobal(pos)) # Show the menu at the global position of the click.
        logger.debug("Editor context menu displayed.")


class DragDropTableWidget(QTableWidget):
    """
    A custom QTableWidget designed for displaying and managing file information.

    It supports:
    - Drag-and-drop of files and folders.
    - Multi-row selection.
    - Custom context menu actions (open file, add/remove tags/suffixes, delete/remove files).
    - Automatic extraction of tags, suffixes, and dates from filenames upon import.
    - Dynamic column headers and visibility based on the active renaming mode.
    - Single-click editing for specific columns without losing multi-row selection.
    """

    # Custom signals for actions that need to be handled by the main window.
    pathsAdded = Signal(int) # Emitted when new paths are successfully added to the table.
    remove_selected_requested = Signal() # Requests removal of selected rows from the table.
    delete_selected_requested = Signal() # Requests permanent deletion of selected files from disk.
    clear_suffix_requested = Signal() # Requests clearing the suffix for selected rows.
    clear_list_requested = Signal() # Requests clearing all items from the list.
    append_suffix_requested = Signal() # Requests appending a suffix to selected rows.

    def __init__(self, parent=None):
        """
        Initializes the DragDropTableWidget.

        Args:
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        logger.info("DragDropTableWidget initialized.")

        # Configure table appearance and behavior.
        self.verticalHeader().setDefaultSectionSize(28) # Adjust row height for better spacing.
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed) # Checkbox column fixed width.
        self.setColumnWidth(0, 24) # Set specific width for the checkbox column.
        self._updating_checks = False # Internal flag to prevent signal loops during checkbox updates.
        self.mode = "normal" # Default renaming mode.
        self.setColumnCount(6) # Define 6 columns: Checkbox, Filename, Tags/Pos/PA_MAT, Date, Suffix, Path.
        self.setHorizontalHeaderLabels(["", "Filename", "Tags", "Date", "Suffix", "Path"]) # Initial header labels.
        
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # Checkbox column resizes to content.
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive) # Filename column interactive.
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive) # Tags/Pos/PA_MAT column interactive.
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # Date column resizes to content.
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents) # Suffix column resizes to content.
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive) # Path column interactive.
        self.setColumnWidth(5, 50) # Set initial width of Path column to be small.
        header.setStretchLastSection(True) # Last column stretches to fill available space.
        
        self.setColumnHidden(0, True) # Initially hide the checkbox column.
        header.sectionDoubleClicked.connect(self.on_header_double_clicked) # Connect double-click on header for auto-resize.
        self.setSortingEnabled(True) # Enable sorting by column.
        self.sortByColumn(1, Qt.SortOrder.AscendingOrder) # Default sort by filename ascending.
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel) # Smooth horizontal scrolling.
        self.setAcceptDrops(True) # Enable drag-and-drop.
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows) # Select entire rows.
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection) # Allow multi-row selection.
        self.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked) # Enable editing on double-click.
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed) # Fixed height for rows.
        self.verticalHeader().setDefaultSectionSize(28) # Ensure consistent row height.
        
        # Connect selection changes to update checkboxes.
        self.selectionModel().selectionChanged.connect(self.on_selection_changed)
        
        self._initial_columns = False # Flag to track if initial column widths have been set.
        # Use a single shot timer to set equal column widths after the UI is fully laid out.
        QTimer.singleShot(0, self.set_equal_column_widths)

        self.setItemDelegate(CustomDelegate(self)) # Apply custom delegate for editor context menu.
        # Install event filter on viewport to intercept clicks for single-click editing.
        self.viewport().installEventFilter(self)
        logger.debug("DragDropTableWidget UI setup complete.")

    def mousePressEvent(self, event: 'QMouseEvent') -> None:
        """
        Overrides mousePressEvent to handle selection behavior.

        If a left-click occurs on an already selected row, it prevents the default
        behavior of clearing the selection, thus preserving multi-row selections.

        Args:
            event (QMouseEvent): The mouse press event.
        """
        if event.button() == Qt.LeftButton:
            index = self.indexAt(event.pos()) # Get the index at the mouse position.
            # If the index is valid and the row is already selected, ignore the event
            # to prevent clearing multi-selection.
            if index.isValid() and self.selectionModel().isSelected(index):
                logger.debug(f"Mouse press on already selected row {index.row()}. Ignoring default selection behavior.")
                return # Do not call super().mousePressEvent to prevent clearing selection.
        super().mousePressEvent(event) # Call base class method for other cases.

    def _create_context_menu(self) -> QMenu:
        """
        Creates and populates the context menu for the table.

        The menu actions are dynamically enabled/disabled based on whether items are selected.

        Returns:
            QMenu: The configured QMenu object.
        """
        menu = QMenu(self)
        has_selection = self.selectionModel().hasSelection() # Check if any rows are selected.
        logger.debug(f"Creating context menu. Has selection: {has_selection}")

        # Action to open the selected file.
        open_action = QAction(tr("open_file"), self)
        open_action.triggered.connect(self.open_selected_file)
        open_action.setEnabled(has_selection)
        menu.addAction(open_action)

        menu.addSeparator()

        # Actions specific to "normal" renaming mode (tags).
        if self.mode == "normal":
            set_tags_action = QAction(tr("add_tags_for_selected"), self)
            set_tags_action.triggered.connect(self.set_tags_for_selected)
            set_tags_action.setEnabled(has_selection)
            menu.addAction(set_tags_action)

            remove_tags_action = QAction(tr("remove_tags_for_selected"), self)
            remove_tags_action.triggered.connect(self.remove_tags_for_selected)
            remove_tags_action.setEnabled(has_selection)
            menu.addAction(remove_tags_action)

        # Actions for suffix management.
        set_suffix_action = QAction(tr("add_suffix_for_selected"), self)
        # Emit a signal to the main window to handle appending suffix for multi-row safety.
        set_suffix_action.triggered.connect(self.append_suffix_requested.emit)
        set_suffix_action.setEnabled(has_selection)
        menu.addAction(set_suffix_action)

        clear_suffix_action = QAction(tr("remove_suffix_for_selected"), self)
        # Emit a signal to the main window to handle clearing suffix.
        clear_suffix_action.triggered.connect(self.clear_suffix_requested.emit)
        clear_suffix_action.setEnabled(has_selection)
        menu.addAction(clear_suffix_action)

        menu.addSeparator()

        # Actions for deleting/removing files.
        delete_selected_action = QAction(tr("delete_selected_files"), self)
        # Emit a signal to the main window to handle file deletion.
        delete_selected_action.triggered.connect(self.delete_selected_requested.emit)
        delete_selected_action.setEnabled(has_selection)
        menu.addAction(delete_selected_action)

        remove_selected_action = QAction(tr("remove_selected"), self)
        # Emit a signal to the main window to handle row removal.
        remove_selected_action.triggered.connect(self.remove_selected_requested.emit)
        remove_selected_action.setEnabled(has_selection)
        menu.addAction(remove_selected_action)

        menu.addSeparator()

        # Action to clear the entire list.
        clear_list_action = QAction(tr("clear_list"), self)
        clear_list_action.triggered.connect(self.clear_list_requested.emit)
        menu.addAction(clear_list_action)

        logger.debug("Context menu created.")
        return menu

    def contextMenuEvent(self, event: 'QContextMenuEvent') -> None:
        """
        Handles the context menu (right-click) event for the table.

        If the table is not in editing state, it ensures the row under the cursor
        is selected (if not already part of a multi-selection) and then displays
        the context menu.

        Args:
            event (QContextMenuEvent): The context menu event.
        """
        # Do not show context menu if an item is currently being edited.
        if self.state() == QAbstractItemView.EditingState:
            logger.debug("Context menu suppressed: table is in editing state.")
            return
        
        pos = event.pos() # Get the position of the mouse click.
        index = self.indexAt(pos) # Get the QModelIndex at that position.
        
        if index.isValid():
            # If the clicked row is not part of the current selection, select only that row.
            # This ensures context actions apply to the clicked item if not multi-selecting.
            if index.row() not in {r.row() for r in self.selectionModel().selectedRows()}: # noqa: C408
                self.selectRow(index.row())
                logger.debug(f"Context menu: Selected row {index.row()} before showing menu.")
        
        menu = self._create_context_menu() # Create the context menu.
        menu.exec_(event.globalPos()) # Display the menu at the global mouse position.
        logger.debug("Context menu event handled.")

    def set_tags_for_selected(self) -> None:
        """
        Prompts the user for tags and adds them to all selected rows.

        This method is typically called from the context menu in "normal" mode.
        It updates the `ItemSettings` object for each selected file and refreshes
        the corresponding table cell.
        """
        selected_rows = self.selectionModel().selectedRows()
        if not selected_rows:
            logger.info("No rows selected to set tags.")
            return

        # Prompt user for comma-separated tags.
        text, ok = QInputDialog.getText(
            self,
            tr("add_tags"),
            tr("enter_comma_separated_tags"),
        )

        if ok and text:
            # Parse input tags, convert to uppercase, and remove empty strings.
            new_tags_to_add = {t.strip().upper() for t in text.split(",") if t.strip()}
            if not new_tags_to_add:
                logger.debug("No valid tags entered to add.")
                return
            logger.info(f"Adding tags {new_tags_to_add} to {len(selected_rows)} selected rows.")
            
            # Iterate through selected rows and update their ItemSettings.
            for index in selected_rows:
                row = index.row()
                item = self.item(row, 1) # Get the QTableWidgetItem holding the file path.
                if not item:
                    logger.warning(f"Item at row {row}, column 1 is None. Skipping tag update.")
                    continue
                settings: ItemSettings = item.data(ROLE_SETTINGS) # Retrieve ItemSettings.
                if not settings:
                    logger.warning(f"ItemSettings not found for row {row}. Skipping tag update.")
                    continue
                
                settings.tags.update(new_tags_to_add) # Add new tags to the existing set.
                
                # Update the tags cell in the table.
                tags_text = ",".join(sorted(settings.tags))
                tags_item = self.item(row, 2) # Get the tags QTableWidgetItem.
                if tags_item:
                    tags_item.setText(tags_text)
                    tags_item.setToolTip(tags_text)
                    logger.debug(f"Updated tags for row {row} to: {tags_text}")
                else:
                    logger.warning(f"Tags item at row {row}, column 2 is None. Cannot update display.")
        elif not ok:
            logger.debug("Add tags dialog canceled.")
        else:
            logger.debug("Add tags dialog accepted but no text entered.")

    def remove_tags_for_selected(self) -> None:
        """
        Prompts the user to either remove specific tags or clear all tags from selected rows.

        This method presents a QMessageBox with options to refine the tag removal process.
        It is typically called from the context menu in "normal" mode.
        """
        selected_rows = self.selectionModel().selectedRows()
        if not selected_rows:
            logger.info("No rows selected to remove tags.")
            return

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(tr("remove_tags"))
        msg_box.setText(tr("remove_tags_question"))
        
        # Add custom buttons for specific actions.
        remove_specific_button = msg_box.addButton(
            tr("remove_specific_tags"), QMessageBox.ActionRole
        )
        clear_all_button = msg_box.addButton(
            tr("clear_all_tags"), QMessageBox.ActionRole
        )
        msg_box.addButton(QMessageBox.Cancel) # Add a Cancel button.

        msg_box.exec() # Show the message box modally.

        clicked_button = msg_box.clickedButton()
        if clicked_button == remove_specific_button:
            self.prompt_for_specific_tags() # Call method to prompt for specific tags.
            logger.debug("User chose to remove specific tags.")
        elif clicked_button == clear_all_button:
            self.clear_all_tags() # Call method to clear all tags.
            logger.debug("User chose to clear all tags.")
        else:
            logger.debug("Tag removal canceled by user.")

    def prompt_for_specific_tags(self) -> None:
        """
        Prompts the user to enter specific tags to remove from selected rows.

        This method is called after the user chooses to remove specific tags
        from the `remove_tags_for_selected` dialog.
        """
        selected_rows = self.selectionModel().selectedRows()
        if not selected_rows:
            logger.info("No rows selected for specific tag removal.")
            return

        text, ok = QInputDialog.getText(
            self,
            tr("remove_specific_tags"),
            tr("enter_comma_separated_tags"),
        )

        if ok and text:
            # Parse tags to remove, convert to uppercase.
            tags_to_remove = {t.strip().upper() for t in text.split(",") if t.strip()}
            if not tags_to_remove:
                logger.debug("No valid tags entered to remove.")
                return
            logger.info(f"Removing specific tags {tags_to_remove} from {len(selected_rows)} selected rows.")
            
            # Iterate through selected rows and update their ItemSettings.
            for index in selected_rows:
                row = index.row()
                item = self.item(row, 1)
                if not item:
                    logger.warning(f"Item at row {row}, column 1 is None. Skipping specific tag removal.")
                    continue
                settings: ItemSettings = item.data(ROLE_SETTINGS)
                if not settings:
                    logger.warning(f"ItemSettings not found for row {row}. Skipping specific tag removal.")
                    continue

                # Remove specified tags from the item's tag set.
                settings.tags.difference_update(tags_to_remove)

                # Update the tags cell in the table.
                tags_text = ",".join(sorted(settings.tags))
                tags_item = self.item(row, 2)
                if tags_item:
                    tags_item.setText(tags_text)
                    tags_item.setToolTip(tags_text)
                    logger.debug(f"Updated tags for row {row} to: {tags_text}")
                else:
                    logger.warning(f"Tags item at row {row}, column 2 is None. Cannot update display.")
        elif not ok:
            logger.debug("Remove specific tags dialog canceled.")
        else:
            logger.debug("Remove specific tags dialog accepted but no text entered.")

    def clear_all_tags(self) -> None:
        """
        Clears all tags from all selected rows.

        This method is called after the user chooses to clear all tags
        from the `remove_tags_for_selected` dialog.
        """
        selected_rows = self.selectionModel().selectedRows()
        if not selected_rows:
            logger.info("No rows selected to clear all tags.")
            return

        logger.info(f"Clearing all tags from {len(selected_rows)} selected rows.")
        # Iterate through selected rows and clear their ItemSettings tags.
        for index in selected_rows:
            row = index.row()
            item = self.item(row, 1)
            if not item:
                logger.warning(f"Item at row {row}, column 1 is None. Skipping clear all tags.")
                continue
            settings: ItemSettings = item.data(ROLE_SETTINGS)
            if not settings:
                logger.warning(f"ItemSettings not found for row {row}. Skipping clear all tags.")
                continue

            settings.tags.clear() # Clear the set of tags.

            # Update the tags cell in the table to be empty.
            tags_item = self.item(row, 2)
            if tags_item:
                tags_item.setText("")
                tags_item.setToolTip("")
                logger.debug(f"Cleared all tags for row {row}.")
            else:
                logger.warning(f"Tags item at row {row}, column 2 is None. Cannot update display.")

    def set_suffix_for_selected(self) -> None:
        """
        Prompts the user for a suffix and appends it to the existing suffix of all selected rows.

        This method is typically called from the context menu.
        """
        selected_rows = self.selectionModel().selectedRows()
        if not selected_rows:
            logger.info("No rows selected to set suffix.")
            return

        text, ok = QInputDialog.getText(
            self,
            tr("add_suffix"),
            tr("enter_suffix"),
        )

        if ok and text:
            suffix_to_append = text.strip()
            if not suffix_to_append:
                logger.debug("No valid suffix entered to append.")
                return
            logger.info(f"Appending suffix '{suffix_to_append}' to {len(selected_rows)} selected rows.")
            
            # Iterate through selected rows and update their ItemSettings suffix.
            for index in selected_rows:
                row = index.row()
                item = self.item(row, 1)
                if not item:
                    logger.warning(f"Item at row {row}, column 1 is None. Skipping suffix update.")
                    continue
                settings: ItemSettings = item.data(ROLE_SETTINGS)
                if not settings:
                    logger.warning(f"ItemSettings not found for row {row}. Skipping suffix update.")
                    continue

                settings.suffix += suffix_to_append # Append the new suffix.
                
                # Update the suffix cell in the table.
                suffix_item = self.item(row, 4)
                if suffix_item:
                    suffix_item.setText(settings.suffix)
                    suffix_item.setToolTip(settings.suffix)
                    logger.debug(f"Updated suffix for row {row} to: {settings.suffix}")
                else:
                    logger.warning(f"Suffix item at row {row}, column 4 is None. Cannot update display.")
        elif not ok:
            logger.debug("Add suffix dialog canceled.")
        else:
            logger.debug("Add suffix dialog accepted but no text entered.")

    def open_selected_file(self) -> None:
        """
        Opens the file associated with the first selected row using the default system application.

        This method is typically called from the context menu.
        """
        selected_rows = self.selectionModel().selectedRows()
        if not selected_rows:
            logger.info("No rows selected to open file.")
            return

        # Get the path from the first selected row.
        first_selected_row = selected_rows[0].row()
        item = self.item(first_selected_row, 1) # Get the QTableWidgetItem holding the file path.
        if item:
            file_path = item.data(Qt.UserRole) # Retrieve the original file path.
            if file_path and os.path.exists(file_path):
                try:
                    # Open the file using the system's default application.
                    QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
                    logger.info(f"Opened file: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to open file {file_path}: {e}")
                    QMessageBox.warning(self, tr("error"), f"Failed to open file {file_path}: {e}")
            else:
                logger.warning(f"File path invalid or does not exist: {file_path}")
                QMessageBox.warning(self, tr("error"), f"File not found or invalid: {file_path}")
        else:
            logger.warning(f"No item found at row {first_selected_row}, column 1 to open.")

    def set_mode(self, mode: str) -> None:
        """
        Switches the table headers and updates cell content based on the given renaming mode.

        This method adjusts column visibility and populates cells with mode-specific data
        (e.g., "Tags" for normal mode, "Pos" for position mode, "PA_MAT" for PA_MAT mode).

        Args:
            mode (str): The renaming mode to set ("normal", "position", or "pa_mat").
        """
        logger.info(f"Setting table mode to: {mode}")
        self.mode = mode # Store the current mode.
        
        # Update horizontal header labels and column visibility based on mode.
        if mode == "position":
            self.setHorizontalHeaderLabels([
                "", "Filename", "Pos", "Date", "Suffix", "Path"
            ])
            self.setColumnHidden(2, False) # Show 'Pos' column.
            self.setColumnHidden(3, True) # Hide 'Date' column.
        elif mode == "pa_mat":
            self.setHorizontalHeaderLabels([
                "", "Filename", "PA_MAT", "Date", "Suffix", "Path"
            ])
            self.setColumnHidden(2, False) # Show 'PA_MAT' column.
            self.setColumnHidden(3, False) # Show 'Date' column.
        else: # Default to "normal" mode.
            self.setHorizontalHeaderLabels(
                ["", "Filename", "Tags", "Date", "Suffix", "Path"]
            )
            self.setColumnHidden(2, False) # Show 'Tags' column.
            self.setColumnHidden(3, False) # Show 'Date' column.

        # Refresh cell content for all rows based on the new mode.
        for row in range(self.rowCount()):
            item1 = self.item(row, 1) # Get the filename item.
            if not item1:
                logger.warning(f"Item at row {row}, column 1 is None during mode switch. Skipping.")
                continue
            settings: ItemSettings = item1.data(ROLE_SETTINGS) # Get ItemSettings.
            if not settings:
                logger.warning(f"ItemSettings not found for row {row} during mode switch. Skipping.")
                continue
            
            # Update specific columns based on the mode.
            if mode == "position":
                pos_item = self.item(row, 2)
                if pos_item:
                    pos_item.setText(settings.position)
                    pos_item.setToolTip(settings.position)
                suf_item = self.item(row, 4)
                if suf_item:
                    suf_item.setText(settings.suffix)
                    suf_item.setToolTip(settings.suffix)
            elif mode == "pa_mat":
                mat_item = self.item(row, 2)
                if mat_item:
                    mat_item.setText(settings.pa_mat)
                    mat_item.setToolTip(settings.pa_mat)
                suf_item = self.item(row, 4)
                if suf_item:
                    suf_item.setText(settings.suffix)
                    suf_item.setToolTip(settings.suffix)
            else: # Normal mode
                tags_item = self.item(row, 2)
                if tags_item:
                    text = ",".join(sorted(settings.tags))
                    tags_item.setText(text)
                    tags_item.setToolTip(text)
                date_item = self.item(row, 3)
                if date_item:
                    date_item.setText(settings.date)
                    date_item.setToolTip(settings.date)
                suf_item = self.item(row, 4)
                if suf_item:
                    suf_item.setText(settings.suffix)
                    suf_item.setToolTip(settings.suffix)
        logger.debug(f"Table mode switched to {mode} and content updated.")

    def set_equal_column_widths(self) -> None:
        """
        Sets equal widths for the interactive columns (Filename, Tags/Pos/PA_MAT, Date, Suffix).

        This method is called once during initialization to distribute available width evenly.
        """
        if self._initial_columns:
            logger.debug("Initial column widths already set. Skipping.")
            return
        self._initial_columns = True
        
        header = self.horizontalHeader()
        # Calculate total available width excluding the fixed-width checkbox column.
        total_width = self.viewport().width() - header.sectionSize(0)
        if total_width <= 0:
            logger.warning("Viewport width is too small to set equal column widths.")
            return
        
        # Distribute width among the 5 interactive columns.
        equal_width = total_width // 5
        for i in range(1, 6):
            self.setColumnWidth(i, equal_width)
        logger.info(f"Set equal column widths to {equal_width}px for interactive columns.")

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        """
        Filters events for the table's viewport to enable single-click editing.

        This allows users to start editing a cell with a single click on specific columns
        (Tags, Date, Suffix) without losing multi-row selection.

        Args:
            source (QObject): The object that received the event (expected to be the viewport).
            event (QEvent): The event that occurred.

        Returns:
            bool: True if the event was handled and should not be propagated further,
                  False otherwise.
        """
        # Only process MouseButtonPress events originating from the viewport.
        if source is self.viewport() and event.type() == QEvent.Type.MouseButtonPress:
            mouse_event = event # Cast to QMouseEvent for button and position.
            index = self.indexAt(mouse_event.pos()) # Get the index at the click position.
            
            if index.isValid():
                # If multiple rows are selected, let the default behavior handle it.
                if len(self.selectionModel().selectedRows()) > 1:
                    logger.debug("Event filter: Multiple rows selected, deferring to default behavior.")
                    return super().eventFilter(source, event)
                
                col = index.column()
                # Define editable columns based on the current mode.
                edit_cols = {2, 4} # Tags/Pos/PA_MAT, Suffix
                if self.mode == "normal" or self.mode == "pa_mat":
                    edit_cols.add(3) # Add Date column for normal and PA_MAT modes.
                
                # If the clicked column is editable, start editing with a single shot timer.
                if col in edit_cols:
                    logger.debug(f"Event filter: Single click on editable column {col}. Starting edit.")
                    # Use singleShot to ensure editing starts after the current event processing.
                    QTimer.singleShot(0, lambda idx=index: self.edit(idx))
                    return True # Event handled.
        
        return super().eventFilter(source, event) # Pass other events to the base class.

    def on_header_double_clicked(self, index: int) -> None:
        """
        Slot to handle double-clicks on horizontal header sections.

        When a header is double-clicked, it resizes the corresponding column
        to fit its contents.

        Args:
            index (int): The logical index of the section that was double-clicked.
        """
        header = self.horizontalHeader()
        # Calculate the optimal width for the column based on its contents.
        new_width = header.sizeHintForColumn(index)
        header.resizeSection(index, new_width) # Apply the new width.
        logger.debug(f"Header section {index} double-clicked. Resized to {new_width}px.")

    def dragEnterEvent(self, event: 'QDragEnterEvent') -> None:
        """
        Handles drag enter events for the table.

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

    def dragMoveEvent(self, event: 'QDragMoveEvent') -> None:
        """
        Handles drag move events for the table.

        Accepts the proposed action if the dragged data contains URLs.

        Args:n            event (QDragMoveEvent): The drag move event.
        """
        if event.mimeData().hasUrls():
            event.acceptProposedAction() # Accept the drag move if it contains file URLs.
            logger.debug("Drag move event accepted (has URLs).")
        else:
            super().dragMoveEvent(event) # Pass to base class if not file URLs.
            logger.debug("Drag move event ignored (no URLs).")

    def dropEvent(self, event: 'QDropEvent') -> None:
        """
        Handles drop events, processing dropped file URLs.

        Extracts file paths from the dropped data, filters them by accepted extensions,
        and adds them to the table.

        Args:
            event (QDropEvent): The drop event.
        """
        if event.mimeData().hasUrls():
            paths_to_add: List[str] = []
            for url in event.mimeData().urls():
                path = self.normalize_path(url.toLocalFile()) # Get local file path and normalize.
                if os.path.isfile(path):
                    ext = os.path.splitext(path)[1].lower()
                    # Check if the file extension is among the accepted types.
                    if ext in ItemSettings.ACCEPT_EXTENSIONS:
                        paths_to_add.append(path)
                        logger.debug(f"Dropped file accepted: {path}")
                    else:
                        logger.warning(f"Dropped file has unsupported extension: {path}")
                else:
                    logger.debug(f"Dropped item is not a file or is a directory: {path}. Directories are handled elsewhere.")
            
            if paths_to_add:
                self.add_paths(paths_to_add) # Add the collected paths to the table.
            event.acceptProposedAction() # Accept the drop action.
        else:
            super().dropEvent(event) # Pass to base class if not file URLs.
            logger.debug("Drop event ignored (no URLs).")

    def add_paths(self, paths: List[str]) -> None:
        """
        Adds a list of file paths to the table.

        For each path, it extracts initial metadata (tags, suffix, date, size),
        creates an `ItemSettings` object, and populates a new row in the table.
        It also handles HEIC conversion during import and avoids duplicates.

        Args:
            paths (List[str]): A list of absolute file paths to add.
        """
        tags_info: Dict[str, str] = {} # Dictionary to store valid tags.
        try:
            tags_info = load_tags() # Load available tags for extraction.
        except Exception as e:
            logger.error(f"Failed to load tags for path addition: {e}. Proceeding with empty tags.")
            tags_info = {}
        
        added_count = 0
        for path_str in paths:
            # Normalize path and convert HEIC if necessary.
            processed_path = self.normalize_path(convert_heic(path_str))
            
            # Check for duplicates before adding.
            is_duplicate = False
            for row_idx in range(self.rowCount()):
                item = self.item(row_idx, 1) # Get the filename item.
                if item and item.data(Qt.UserRole) == processed_path:
                    is_duplicate = True
                    logger.info(f"Skipping duplicate file: {processed_path}")
                    break
            
            if is_duplicate:
                continue
            
            # Insert a new row at the end of the table.
            row = self.rowCount()
            self.insertRow(row)

            # Column 0: Checkbox for selection.
            check_item = QTableWidgetItem()
            check_item.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
            )
            check_item.setCheckState(Qt.CheckState.Unchecked)

            # Column 1: Filename and original path (UserRole).
            fname_item = QTableWidgetItem(os.path.basename(processed_path))
            fname_item.setData(Qt.ItemDataRole.UserRole, processed_path) # Store full path.

            # Extract tags, suffix, and date from the filename/metadata.
            extracted_tags: Set[str] = set()
            try:
                extracted_tags = extract_tags_from_name(processed_path, tags_info.keys())
            except Exception as e:
                logger.warning(f"Failed to extract tags from {processed_path}: {e}")
            
            extracted_suffix: str = ""
            try:
                extracted_suffix = extract_suffix_from_name(processed_path, tags_info.keys(), mode=self.mode)
            except Exception as e:
                logger.warning(f"Failed to extract suffix from {processed_path}: {e}")
            
            capture_date: str = get_capture_date(processed_path) # Get capture date.
            
            file_size_bytes: int = 0
            try:
                file_size_bytes = os.path.getsize(processed_path)
            except OSError as e:
                logger.error(f"Could not get size of file {processed_path}: {e}")

            # Create and store ItemSettings object for the row.
            settings = ItemSettings(
                processed_path,
                tags=extracted_tags,
                suffix=extracted_suffix,
                date=capture_date,
                size_bytes=file_size_bytes,
                compressed_bytes=file_size_bytes, # Initially, compressed size is same as original.
            )
            fname_item.setData(ROLE_SETTINGS, settings) # Store ItemSettings in custom role.

            # Column 2: Tags (or Pos/PA_MAT depending on mode).
            tags_item = QTableWidgetItem(",".join(sorted(extracted_tags)))
            tags_item.setToolTip(",".join(sorted(extracted_tags)))
            
            # Column 3: Date.
            date_item = QTableWidgetItem(capture_date)
            date_item.setToolTip(capture_date)
            
            # Column 4: Suffix.
            suffix_item = QTableWidgetItem(extracted_suffix)
            suffix_item.setToolTip(extracted_suffix)

            # Column 5: Path.
            path_item = QTableWidgetItem(processed_path)
            path_item.setToolTip(processed_path)
            
            # Set all items in the new row.
            self.setItem(row, 0, check_item)
            self.setItem(row, 1, fname_item)
            self.setItem(row, 2, tags_item)
            self.setItem(row, 3, date_item)
            self.setItem(row, 4, suffix_item)
            self.setItem(row, 5, path_item)
            added_count += 1
            logger.debug(f"Added row for file: {processed_path}")

        # If any files were added and no row is currently selected, select the first row.
        if self.rowCount() > 0 and not self.selectionModel().hasSelection():
            self.selectRow(0)
            logger.debug("Selected first row after adding paths.")
        
        if added_count > 0:
            self.sortByColumn(1, Qt.AscendingOrder) # Re-sort the table by filename.
            self.pathsAdded.emit(added_count) # Emit signal indicating paths were added.
            logger.info(f"Successfully added {added_count} new paths to the table.")

    def normalize_path(self, path: str) -> str:
        """
        Normalizes a file path by replacing backslashes with forward slashes.

        This ensures path consistency across different operating systems.

        Args:
            path (str): The file path to normalize.

        Returns:
            str: The normalized file path.
        """
        return path.replace("\\", "/")

    def get_item_by_row(self, row: int) -> ItemSettings | None:
        """
        Retrieves the `ItemSettings` object associated with a given table row.

        Args:
            row (int): The row index in the table.

        Returns:
            ItemSettings | None: The `ItemSettings` object if found, otherwise None.
        """
        item0 = self.item(row, 1) # Get the item in the filename column.
        if not item0:
            logger.warning(f"No item found at row {row}, column 1. Cannot retrieve ItemSettings.")
            return None
        settings: ItemSettings = item0.data(ROLE_SETTINGS)
        if not settings:
            logger.warning(f"No ItemSettings found for item at row {row}, column 1.")
        return settings

    def on_selection_changed(
        self, selected: QItemSelection, deselected: QItemSelection
    ) -> None:
        """
        Slot to update the visibility of row checkboxes when the table selection changes.

        This ensures that the checkbox in column 0 accurately reflects the row's selection state.

        Args:
            selected (QItemSelection): The selection of newly selected items.
            deselected (QItemSelection): The selection of newly deselected items.
        """
        # Collect rows that are now selected or deselected.
        to_check = {index.row() for index in selected.indexes()}
        to_uncheck = {index.row() for index in deselected.indexes()}
        
        if not to_check and not to_uncheck:
            logger.debug("Selection changed signal received but no rows actually changed state.")
            return
        
        # Set a flag to prevent recursive calls to itemChanged during programmatic updates.
        self._updating_checks = True
        logger.debug(f"Updating checkboxes for {len(to_check)} selected and {len(to_uncheck)} deselected rows.")
        
        # Update checkboxes for newly selected rows.
        for row in to_check:
            item = self.item(row, 0) # Get the checkbox item.
            if item:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                logger.warning(f"Checkbox item at row {row}, column 0 is None during selection change.")
        
        # Update checkboxes for newly deselected rows.
        for row in to_uncheck:
            item = self.item(row, 0)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)
            else:
                logger.warning(f"Checkbox item at row {row}, column 0 is None during deselection change.")
        
        self._updating_checks = False # Reset the flag.

    def sync_check_column(self) -> None:
        """
        Synchronizes the check state of the checkbox column (column 0) with the row selection state.

        This method ensures that if a row is selected, its checkbox is checked, and vice-versa.
        It is useful after programmatic changes to selection or data.
        """
        selected_rows = {idx.row() for idx in self.selectionModel().selectedRows()}
        logger.debug("Synchronizing check column with selection.")
        self._updating_checks = True # Prevent itemChanged signal during update.
        for row in range(self.rowCount()):
            item = self.item(row, 0) # Get the checkbox item.
            if not item:
                logger.warning(f"Checkbox item at row {row}, column 0 is None during sync. Skipping.")
                continue
            # Set check state based on whether the row is in the selected set.
            item.setCheckState(Qt.CheckState.Checked if row in selected_rows else Qt.CheckState.Unchecked)
        self._updating_checks = False

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        Overrides keyPressEvent to enable specific keyboard interactions.

        - Allows starting cell editing with any text input if not already editing.
        - Handles Enter/Return key to move focus to the next row in editable columns
          and immediately start editing that cell.

        Args:
            event (QKeyEvent): The key press event.
        """
        index = self.currentIndex() # Get the currently focused cell's index.
        
        # Define columns that are typically editable.
        edit_cols = {2, 4} # Tags/Pos/PA_MAT, Suffix
        if self.mode == "normal" or self.mode == "pa_mat":
            edit_cols.add(3) # Add Date column for normal and PA_MAT modes.

        # Check if the current index is valid and in an editable column.
        if index.isValid() and index.column() in edit_cols:
            # If multiple rows are selected, let the default key press event handle it.
            if len(self.selectionModel().selectedRows()) > 1:
                logger.debug("Key press: Multiple rows selected, deferring to default behavior.")
                super().keyPressEvent(event)
                return

            # Handle Enter/Return key press.
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                row_before = index.row()
                col = index.column()
                
                # If currently on the same row and not the last row, move to the next row and start editing.
                if self.currentRow() == row_before and row_before < self.rowCount() - 1:
                    next_row = row_before + 1
                    self.setCurrentCell(next_row, col) # Move focus to the next row.
                    self.selectRow(next_row) # Select the new row.
                    # Use singleShot to ensure editing starts after the current event processing.
                    QTimer.singleShot(0, lambda: self.edit(self.currentIndex()))
                    logger.debug(f"Enter key: Moved focus to row {next_row} and started editing.")
                return # Event handled.

            # If not currently editing and a printable character is pressed, start editing.
            if self.state() != QAbstractItemView.State.EditingState and event.text():
                self.edit(index) # Start editing the current cell.
                logger.debug(f"Key press: Started editing cell {index.row()},{index.column()} with text '{event.text()}\'.")
                super().keyPressEvent(event) # Pass the event to the editor.
                return

        super().keyPressEvent(event) # Pass other key events to the base class.