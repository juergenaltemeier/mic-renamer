"""Table widget with drag and drop support."""

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
)
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtCore import (
    Qt,
    QTimer,
    QItemSelection,
     QEvent,
    Signal,
    QUrl,
)

from ...logic.settings import ItemSettings
from ...logic.tag_loader import load_tags
from ...logic.tag_service import extract_tags_from_name, extract_suffix_from_name
from ...logic.heic_converter import convert_heic
from ...utils.i18n import tr
from ...utils.meta_utils import get_capture_date

from PySide6.QtWidgets import QLineEdit

ROLE_SETTINGS = Qt.UserRole + 1
log = logging.getLogger(__name__)


class CustomDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            editor.setContextMenuPolicy(Qt.CustomContextMenu)
            editor.customContextMenuRequested.connect(self.show_editor_context_menu)
        return editor

    def show_editor_context_menu(self, pos):
        editor = self.sender()
        if not isinstance(editor, QLineEdit):
            return

        table = self.parent()
        if not isinstance(table, DragDropTableWidget):
            return

        menu = table._create_context_menu()
        menu.exec_(editor.mapToGlobal(pos))


class DragDropTableWidget(QTableWidget):
    """Table widget supporting drag-and-drop and multi-select."""
    def mousePressEvent(self, event):
        # Preserve multi-row selection when clicking on already-selected rows
        if event.button() == Qt.LeftButton:
            index = self.indexAt(event.pos())
            if index.isValid() and self.selectionModel().isSelected(index):
                # Do not clear existing selection; ignore selection change
                return
        super().mousePressEvent(event)
    pathsAdded = Signal(int)
    remove_selected_requested = Signal()
    delete_selected_requested = Signal()
    clear_suffix_requested = Signal()
    clear_list_requested = Signal()
    # Signal to request appending a suffix to selected rows
    append_suffix_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # adjust row height for better spacing
        self.verticalHeader().setDefaultSectionSize(28)
        # set first column (checkbox) to fixed width
        from PySide6.QtWidgets import QHeaderView
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.setColumnWidth(0, 24)
        self._updating_checks = False
        self.mode = "normal"
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(["", "Filename", "Tags", "Date", "Suffix"])
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        # hide first (checkbox) column when selections are made by row clicks only
        self.setColumnHidden(0, True)
        header.sectionDoubleClicked.connect(self.on_header_double_clicked)
        self.setSortingEnabled(True)
        self.sortByColumn(1, Qt.SortOrder.AscendingOrder)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setAcceptDrops(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        # ensure consistent row height
        self.verticalHeader().setDefaultSectionSize(28)
        self.selectionModel().selectionChanged.connect(self.on_selection_changed)
        # removed internal cellChanged handler to avoid double state updates and conflicts
        # self.cellChanged.connect(self._on_cell_changed)
        self._initial_columns = False
        QTimer.singleShot(0, self.set_equal_column_widths)

        self.setItemDelegate(CustomDelegate(self))
        # allow intercepting clicks for single-click editing
        self.viewport().installEventFilter(self)

    def _create_context_menu(self):
        menu = QMenu(self)
        has_selection = self.selectionModel().hasSelection()

        open_action = QAction(tr("open_file"), self)
        open_action.triggered.connect(self.open_selected_file)
        open_action.setEnabled(has_selection)
        menu.addAction(open_action)

        menu.addSeparator()

        if self.mode == "normal":
            set_tags_action = QAction(tr("add_tags_for_selected"), self)
            set_tags_action.triggered.connect(self.set_tags_for_selected)
            set_tags_action.setEnabled(has_selection)
            menu.addAction(set_tags_action)

            remove_tags_action = QAction(tr("remove_tags_for_selected"), self)
            remove_tags_action.triggered.connect(self.remove_tags_for_selected)
            remove_tags_action.setEnabled(has_selection)
            menu.addAction(remove_tags_action)

        set_suffix_action = QAction(tr("add_suffix_for_selected"), self)
        # delegate suffix-appending to main window for multi-row safety
        set_suffix_action.triggered.connect(self.append_suffix_requested.emit)
        set_suffix_action.setEnabled(has_selection)
        menu.addAction(set_suffix_action)

        clear_suffix_action = QAction(tr("remove_suffix_for_selected"), self)
        clear_suffix_action.triggered.connect(self.clear_suffix_requested.emit)
        clear_suffix_action.setEnabled(has_selection)
        menu.addAction(clear_suffix_action)

        menu.addSeparator()

        delete_selected_action = QAction(tr("delete_selected_files"), self)
        delete_selected_action.triggered.connect(self.delete_selected_requested.emit)
        delete_selected_action.setEnabled(has_selection)
        menu.addAction(delete_selected_action)

        remove_selected_action = QAction(tr("remove_selected"), self)
        remove_selected_action.triggered.connect(self.remove_selected_requested.emit)
        remove_selected_action.setEnabled(has_selection)
        menu.addAction(remove_selected_action)

        menu.addSeparator()

        clear_list_action = QAction(tr("clear_list"), self)
        clear_list_action.triggered.connect(self.clear_list_requested.emit)
        menu.addAction(clear_list_action)

        return menu

    def contextMenuEvent(self, event):
        # On right-click, select the row under cursor for context actions
        if self.state() == QAbstractItemView.EditingState:
            return
        pos = event.pos()
        index = self.indexAt(pos)
        if index.isValid():
            # select only the clicked row if not already selected
            if index.row() not in {r.row() for r in self.selectionModel().selectedRows()}:  # noqa: C408
                self.selectRow(index.row())
        menu = self._create_context_menu()
        menu.exec_(event.globalPos())

    def set_tags_for_selected(self):
        selected_rows = self.selectionModel().selectedRows()
        if not selected_rows:
            return

        text, ok = QInputDialog.getText(
            self,
            tr("add_tags"),
            tr("enter_comma_separated_tags"),
        )

        if ok and text:
            new_tags_to_add = {t.strip().upper() for t in text.split(",") if t.strip()}
            for index in selected_rows:
                row = index.row()
                item = self.item(row, 1)
                if not item:
                    continue
                settings = item.data(ROLE_SETTINGS)
                if not settings:
                    continue
                
                settings.tags.update(new_tags_to_add)
                
                tags_text = ",".join(sorted(settings.tags))
                tags_item = self.item(row, 2)
                if tags_item:
                    tags_item.setText(tags_text)
                    tags_item.setToolTip(tags_text)

    def remove_tags_for_selected(self):
        selected_rows = self.selectionModel().selectedRows()
        if not selected_rows:
            return

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(tr("remove_tags"))
        msg_box.setText(tr("remove_tags_question"))
        remove_specific_button = msg_box.addButton(
            tr("remove_specific_tags"), QMessageBox.ActionRole
        )
        clear_all_button = msg_box.addButton(
            tr("clear_all_tags"), QMessageBox.ActionRole
        )
        msg_box.addButton(QMessageBox.Cancel)

        msg_box.exec()

        clicked_button = msg_box.clickedButton()
        if clicked_button == remove_specific_button:
            self.prompt_for_specific_tags()
        elif clicked_button == clear_all_button:
            self.clear_all_tags()

    def prompt_for_specific_tags(self):
        selected_rows = self.selectionModel().selectedRows()
        if not selected_rows:
            return

        text, ok = QInputDialog.getText(
            self,
            tr("remove_specific_tags"),
            tr("enter_comma_separated_tags"),
        )

        if ok and text:
            tags_to_remove = {t.strip().upper() for t in text.split(",") if t.strip()}
            log.debug(f"Removing specific tags: {tags_to_remove}")
            for index in selected_rows:
                row = index.row()
                item = self.item(row, 1)
                if not item:
                    continue
                settings = item.data(ROLE_SETTINGS)
                if not settings:
                    continue

                settings.tags.difference_update(tags_to_remove)

                tags_text = ",".join(sorted(settings.tags))
                tags_item = self.item(row, 2)
                if tags_item:
                    tags_item.setText(tags_text)
                    tags_item.setToolTip(tags_text)

    def clear_all_tags(self):
        selected_rows = self.selectionModel().selectedRows()
        if not selected_rows:
            return

        log.debug("Clearing all tags from selected rows")
        for index in selected_rows:
            row = index.row()
            item = self.item(row, 1)
            if not item:
                continue
            settings = item.data(ROLE_SETTINGS)
            if not settings:
                continue

            settings.tags.clear()

            tags_item = self.item(row, 2)
            if tags_item:
                tags_item.setText("")
                tags_item.setToolTip("")

    def set_suffix_for_selected(self):
        selected_rows = self.selectionModel().selectedRows()
        if not selected_rows:
            return

        text, ok = QInputDialog.getText(
            self,
            tr("add_suffix"),
            tr("enter_suffix"),
        )

        if ok and text:
            suffix_to_append = text.strip()
            for index in selected_rows:
                row = index.row()
                item = self.item(row, 1)
                if not item:
                    continue
                settings = item.data(ROLE_SETTINGS)
                if not settings:
                    continue

                settings.suffix += suffix_to_append
                
                suffix_item = self.item(row, 4)
                if suffix_item:
                    suffix_item.setText(settings.suffix)
                    suffix_item.setToolTip(settings.suffix)

    def open_selected_file(self):
        selected_rows = self.selectionModel().selectedRows()
        if not selected_rows:
            return

        first_selected_row = selected_rows[0].row()
        item = self.item(first_selected_row, 1)
        if item:
            file_path = item.data(Qt.UserRole)
            if file_path and os.path.exists(file_path):
                QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))

    def set_mode(self, mode: str) -> None:
        """Switch table headers for the given mode."""
        self.mode = mode
        if mode == "position":
            self.setHorizontalHeaderLabels([
                "", "Filename", "Pos", "Date", "Suffix"
            ])
            self.setColumnHidden(2, True)
            self.setColumnHidden(3, True)
        elif mode == "pa_mat":
            self.setHorizontalHeaderLabels([
                "", "Filename", "PA_MAT", "Date", "Suffix"
            ])
            self.setColumnHidden(2, True)
            self.setColumnHidden(3, False)
        else:
            self.setHorizontalHeaderLabels(
                ["", "Filename", "Tags", "Date", "Suffix"]
            )
            self.setColumnHidden(2, False)
            self.setColumnHidden(3, False)
        for row in range(self.rowCount()):
            item1 = self.item(row, 1)
            if not item1:
                continue
            settings: ItemSettings = item1.data(ROLE_SETTINGS)
            if not settings:
                continue
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
            else:
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

    def set_equal_column_widths(self):
        if self._initial_columns:
            return
        self._initial_columns = True
        header = self.horizontalHeader()
        total = self.viewport().width() - header.sectionSize(0)
        if total <= 0:
            return
        w = total // 4
        for i in range(1, 5):
            self.setColumnWidth(i, w)

    # ------------------------------------------------------------------
    # Event filter to enable single-click editing without losing
    # the current multi-row selection.
    # ------------------------------------------------------------------
    def eventFilter(self, source, event):
        if source is self.viewport() and event.type() == QEvent.Type.MouseButtonPress:
            index = self.indexAt(event.pos())
            if index.isValid():
                if len(self.selectionModel().selectedRows()) > 1:
                    return super().eventFilter(source, event)
                col = index.column()
                edit_cols = [2, 4]
                if self.mode == "normal" or self.mode == "pa_mat":
                    edit_cols.append(3)  # Add date column for normal mode
                if col in edit_cols:
                    QTimer.singleShot(0, lambda idx=index: self.edit(idx))
        return super().eventFilter(source, event)

    # Removed internal cellChanged handler; on_table_item_changed in main_window now handles edits

    def on_header_double_clicked(self, index: int):
        header = self.horizontalHeader()
        new_width = header.sizeHintForColumn(index)
        header.resizeSection(index, new_width)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            paths = []
            for url in event.mimeData().urls():
                path = self.normalize_path(url.toLocalFile())
                if os.path.isfile(path):
                    ext = os.path.splitext(path)[1].lower()
                    if ext in ItemSettings.ACCEPT_EXTENSIONS:
                        paths.append(path)
            self.add_paths(paths)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def add_paths(self, paths: list[str]):
        tags_info = {}
        try:
            tags_info = load_tags()
        except Exception:
            tags_info = {}
        added = 0
        for path in paths:
            path = self.normalize_path(convert_heic(path))
            duplicate = False
            for row in range(self.rowCount()):
                item = self.item(row, 1)
                if item and item.data(Qt.UserRole) == path:
                    duplicate = True
                    break
            if duplicate:
                continue
            row = self.rowCount()
            self.insertRow(row)
            check_item = QTableWidgetItem()
            # enable checkable, selectable, and enabled so clicking selects the row
            check_item.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable |
                Qt.ItemFlag.ItemIsSelectable |
                Qt.ItemFlag.ItemIsEnabled
            )
            check_item.setCheckState(Qt.CheckState.Unchecked)
            fname_item = QTableWidgetItem(os.path.basename(path))
            fname_item.setData(Qt.ItemDataRole.UserRole, path)

            tags = set()
            try:
                tags = extract_tags_from_name(path, tags_info.keys())
            except Exception:
                tags = set()
            suffix = ""
            try:
                suffix = extract_suffix_from_name(path, tags_info.keys(), mode=self.mode)
            except Exception:
                suffix = ""
            date = get_capture_date(path)
            size_bytes = os.path.getsize(path)
            settings = ItemSettings(
                path,
                tags=tags,
                suffix=suffix,
                date=date,
                size_bytes=size_bytes,
                compressed_bytes=size_bytes,
            )
            fname_item.setData(ROLE_SETTINGS, settings)

            tags_item = QTableWidgetItem(",".join(sorted(tags)))
            date_item = QTableWidgetItem(date)
            suffix_item = QTableWidgetItem(suffix)
            tags_item.setToolTip(",".join(sorted(tags)))
            date_item.setToolTip(date)
            suffix_item.setToolTip(suffix)
            self.setItem(row, 0, check_item)
            self.setItem(row, 1, fname_item)
            self.setItem(row, 2, tags_item)
            self.setItem(row, 3, date_item)
            self.setItem(row, 4, suffix_item)
            added += 1
        if self.rowCount() > 0 and not self.selectionModel().hasSelection():
            self.selectRow(0)
        if added:
            self.sortByColumn(1, Qt.AscendingOrder)
            self.pathsAdded.emit(added)

    def normalize_path(self, path: str) -> str:
        return path.replace("\\", "/")

    def get_item_by_row(self, row: int) -> ItemSettings | None:
        """Return the ItemSettings for the given table row."""
        item0 = self.item(row, 1)
        if not item0:
            return None
        return item0.data(ROLE_SETTINGS)

    def on_selection_changed(
        self, selected: QItemSelection, deselected: QItemSelection
    ) -> None:
        """Update row checkboxes when the selection changes."""
        to_check = {index.row() for index in selected.indexes()}
        to_uncheck = {index.row() for index in deselected.indexes()}
        if not to_check and not to_uncheck:
            return
        self._updating_checks = True
        for row in to_check:
            item = self.item(row, 0)
            if item:
                item.setCheckState(Qt.CheckState.Checked)
        for row in to_uncheck:
            item = self.item(row, 0)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)
        self._updating_checks = False

    def sync_check_column(self):
        selected = {idx.row() for idx in self.selectionModel().selectedRows()}
        self._updating_checks = True
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            if not item:
                continue
            item.setCheckState(Qt.CheckState.Checked if row in selected else Qt.CheckState.Unchecked)
        self._updating_checks = False

    def mousePressEvent(self, event):
        index = self.indexAt(event.pos())
        if index.isValid():
            if index.column() == 4 or (
                index.column() == 2 and self.mode == "normal"
            ) or (index.column() == 3 and self.mode == "normal"):
                self._selection_before_edit = [
                    idx.row() for idx in self.selectionModel().selectedRows()
                ]
        super().mousePressEvent(event)

    def keyPressEvent(self, event):  # noqa: D401
        """Start editing via keyboard and move to the next row on Enter."""
        index = self.currentIndex()
        edit_cols = {2, 4}
        if self.mode == "normal" or self.mode == "pa_mat":
            edit_cols.add(3)

        if index.isValid() and index.column() in edit_cols:
            if len(self.selectionModel().selectedRows()) > 1:
                super().keyPressEvent(event)
                return

            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                row_before = index.row()
                col = index.column()
                # Do not call super().keyPressEvent(event) here to avoid interfering with editing
                if self.currentRow() == row_before and row_before < self.rowCount() - 1:
                    next_row = row_before + 1
                    self.setCurrentCell(next_row, col)
                    self.selectRow(next_row)
                    QTimer.singleShot(0, lambda: self.edit(self.currentIndex()))
                return

            if self.state() != QAbstractItemView.State.EditingState and event.text():
                self.edit(index)
                super().keyPressEvent(event)
                return

        super().keyPressEvent(event)