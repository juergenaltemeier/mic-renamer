"""Table widget with drag and drop support."""

import os
from PySide6.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QApplication,
    QAbstractItemView,
)
from PySide6.QtGui import QPalette

# QItemSelectionModel and QItemSelection are in QtCore, not QtWidgets
from PySide6.QtCore import Qt, QTimer, QItemSelectionModel, QItemSelection
from importlib import resources

from ...logic.settings import ItemSettings
from ...logic.tag_loader import load_tags
from ...logic.tag_service import extract_tags_from_name
from ...logic.heic_converter import convert_heic
from ...utils.meta_utils import get_capture_date

ROLE_SETTINGS = Qt.UserRole + 1


class DragDropTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._updating_checks = False
        self.mode = "normal"
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(
            ["", "Filename", "Tags", "Date", "Suffix"]
        )
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
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
        self._selection_before_edit: list[int] = []
        self._initial_columns = False
        QTimer.singleShot(0, self.set_equal_column_widths)

        logo = resources.files("mic_renamer") / "favicon.png"
        if logo.is_file():
            style = (
                "QTableWidget::viewport{"
                f"background-image:url('{logo.as_posix()}');"
                "background-repeat:no-repeat;"
                "background-position:center;}"
            )
            self.setStyleSheet(style)

    def set_mode(self, mode: str) -> None:
        """Switch table headers for the given mode."""
        self.mode = mode
        if mode == "position":
            self.setHorizontalHeaderLabels(
                ["", "Filename", "Pos", "Date", "Suffix"]
            )
            self.setColumnHidden(3, True)
        else:
            self.setHorizontalHeaderLabels(
                ["", "Filename", "Tags", "Date", "Suffix"]
            )
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
        tags_info = {}
        try:
            tags_info = load_tags()
        except Exception:
            tags_info = {}
        for path in paths:
            path = convert_heic(path)
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
            palette = QApplication.palette()
            fname_item.setBackground(palette.color(QPalette.Base))
            fname_item.setForeground(palette.color(QPalette.Text))

            tags = set()
            try:
                tags = extract_tags_from_name(path, tags_info.keys())
            except Exception:
                tags = set()
            date = get_capture_date(path)
            size_bytes = os.path.getsize(path)
            settings = ItemSettings(
                path,
                tags=tags,
                date=date,
                size_bytes=size_bytes,
                compressed_bytes=size_bytes,
            )
            fname_item.setData(ROLE_SETTINGS, settings)

            tags_item = QTableWidgetItem(",".join(sorted(tags)))
            date_item = QTableWidgetItem(date)
            suffix_item = QTableWidgetItem("")
            tags_item.setToolTip(",".join(sorted(tags)))
            date_item.setToolTip(date)
            suffix_item.setToolTip("")
            self.setItem(row, 0, check_item)
            self.setItem(row, 1, fname_item)
            self.setItem(row, 2, tags_item)
            self.setItem(row, 3, date_item)
            self.setItem(row, 4, suffix_item)
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
            self.selectionModel().select(
                selection, command | QItemSelectionModel.Rows
            )
        else:
            if item.checkState() == Qt.Checked:
                self.selectionModel().select(
                    index,
                    QItemSelectionModel.Select | QItemSelectionModel.Rows,
                )
            else:
                self.selectionModel().select(
                    index,
                    QItemSelectionModel.Deselect | QItemSelectionModel.Rows,
                )

    def mousePressEvent(self, event):
        index = self.indexAt(event.pos())
        if index.isValid():
            if index.column() == 4 or (
                index.column() == 2 and self.mode == "normal"
            ):
                self._selection_before_edit = [
                    idx.row() for idx in self.selectionModel().selectedRows()
                ]
        super().mousePressEvent(event)
