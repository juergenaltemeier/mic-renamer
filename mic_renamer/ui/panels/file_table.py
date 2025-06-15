"""Table widget with drag and drop support."""
import os
from PySide6.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QApplication,
    QItemSelectionModel,
    QItemSelection,
    QAbstractItemView,
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt, QTimer

from ...logic.settings import ItemSettings


class DragDropTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._updating_checks = False
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["", "Filename", "Tags", "Suffix"])
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setStretchLastSection(True)
        header.sectionDoubleClicked.connect(self.on_header_double_clicked)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setAcceptDrops(True)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.ExtendedSelection)
        self.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.verticalHeader().setDefaultSectionSize(24)
        self.itemSelectionChanged.connect(self.sync_check_column)
        self.itemChanged.connect(self.handle_item_changed)
        self._initial_columns = False
        QTimer.singleShot(0, self.set_equal_column_widths)

    def set_equal_column_widths(self):
        if self._initial_columns:
            return
        self._initial_columns = True
        header = self.horizontalHeader()
        total = self.viewport().width() - header.sectionSize(0)
        if total <= 0:
            return
        w = total // 3
        for i in range(1, 4):
            self.setColumnWidth(i, w)

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
                path = url.toLocalFile()
                if os.path.isfile(path):
                    ext = os.path.splitext(path)[1].lower()
                    if ext in ItemSettings.ACCEPT_EXTENSIONS:
                        paths.append(path)
            self.add_paths(paths)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def add_paths(self, paths: list[str]):
        for path in paths:
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
            check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            check_item.setCheckState(Qt.Unchecked)
            fname_item = QTableWidgetItem(os.path.basename(path))
            fname_item.setData(Qt.UserRole, path)
            fname_item.setBackground(QColor(30, 30, 30))
            fname_item.setForeground(QColor(220, 220, 220))
            tags_item = QTableWidgetItem("")
            suffix_item = QTableWidgetItem("")
            tags_item.setToolTip("")
            suffix_item.setToolTip("")
            self.setItem(row, 0, check_item)
            self.setItem(row, 1, fname_item)
            self.setItem(row, 2, tags_item)
            self.setItem(row, 3, suffix_item)
        if self.rowCount() > 0 and not self.selectionModel().hasSelection():
            self.selectRow(0)

    def sync_check_column(self):
        selected = {idx.row() for idx in self.selectionModel().selectedRows()}
        self._updating_checks = True
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            if not item:
                continue
            item.setCheckState(Qt.Checked if row in selected else Qt.Unchecked)
        self._updating_checks = False

    def handle_item_changed(self, item: QTableWidgetItem):
        if self._updating_checks or item.column() != 0:
            return
        row = item.row()
        index = self.model().index(row, 0)
        mods = QApplication.keyboardModifiers()
        if mods & Qt.ShiftModifier and self.selectionModel().hasSelection():
            cur = self.selectionModel().currentIndex().row()
            start = min(cur, row)
            end = max(cur, row)
            selection = QItemSelection(
                self.model().index(start, 0),
                self.model().index(end, self.columnCount() - 1),
            )
            command = (
                QItemSelectionModel.Select
                if item.checkState() == Qt.Checked
                else QItemSelectionModel.Deselect
            )
            self.selectionModel().select(selection, command | QItemSelectionModel.Rows)
        else:
            if item.checkState() == Qt.Checked:
                self.selectionModel().select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
            else:
                self.selectionModel().select(index, QItemSelectionModel.Deselect | QItemSelectionModel.Rows)
