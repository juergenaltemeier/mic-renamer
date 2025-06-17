from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QDialogButtonBox,
)
from PySide6.QtCore import Qt
import os

from ..logic.image_compressor import ImageCompressor
from ..utils.i18n import tr
from .. import config_manager
from .panels.media_viewer import MediaViewer


class CompressionDialog(QDialog):
    """Dialog showing compression progress and results."""

    def __init__(self, rows_and_paths: list[tuple[int, str]], convert_heic: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("compression_window_title"))
        self.results: list[tuple[int, str, int, int]] = []
        layout = QVBoxLayout(self)

        self.viewer = MediaViewer()
        layout.addWidget(self.viewer)

        self.table = QTableWidget(len(rows_and_paths), 4)
        self.table.setHorizontalHeaderLabels([
            tr("file"),
            tr("old_size"),
            tr("new_size"),
            tr("reduction"),
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(btns)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

        cfg = config_manager.load()
        compressor = ImageCompressor(
            max_size_kb=cfg.get("compression_max_size_kb", 2048),
            quality=cfg.get("compression_quality", 95),
            reduce_resolution=cfg.get("compression_reduce_resolution", True),
            resize_only=cfg.get("compression_resize_only", False),
        )

        for row, path in rows_and_paths:
            self.viewer.load_path(path)
            old_size = os.path.getsize(path)
            new_path, new_size, reduction = compressor.compress(path, convert_heic)
            self.table.setItem(row, 0, QTableWidgetItem(os.path.basename(new_path)))
            self.table.setItem(row, 1, QTableWidgetItem(f"{old_size // 1024} KB"))
            self.table.setItem(row, 2, QTableWidgetItem(f"{new_size // 1024} KB"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{reduction}%"))
            self.results.append((row, new_path, old_size, new_size))
        if self.table.rowCount() > 0:
            self.table.selectRow(0)
            self.viewer.load_path(rows_and_paths[0][1])

        self.table.currentCellChanged.connect(self.on_row_changed)

    def on_row_changed(self, row: int, *_):
        item = self.table.item(row, 0)
        if not item:
            return
        path = None
        for r, p, *_ in self.results:
            if r == row:
                path = p
                break
        if path:
            self.viewer.load_path(path)

