from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QDialogButtonBox,
)
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
        self._paths: list[str] = []
        layout = QVBoxLayout(self)

        self.viewer = MediaViewer()
        layout.addWidget(self.viewer)

        valid = [rp for rp in rows_and_paths if os.path.isfile(rp[1])]
        self.table = QTableWidget(len(valid), 4)
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
            max_width=cfg.get("compression_max_width", 0) or None,
            max_height=cfg.get("compression_max_height", 0) or None,
        )

        row_idx = 0
        for row, path in valid:
            self.viewer.load_path(path)
            old_size = os.path.getsize(path)
            new_path, new_size, reduction = compressor.compress(path, convert_heic)
            self.table.setItem(row_idx, 0, QTableWidgetItem(os.path.basename(new_path)))
            self.table.setItem(row_idx, 1, QTableWidgetItem(f"{old_size // 1024} KB"))
            self.table.setItem(row_idx, 2, QTableWidgetItem(f"{new_size // 1024} KB"))
            self.table.setItem(row_idx, 3, QTableWidgetItem(f"{reduction}%"))
            self.results.append((row, new_path, old_size, new_size))
            self._paths.append(new_path)
            row_idx += 1
        if self.table.rowCount() > 0:
            self.table.selectRow(0)
            self.viewer.load_path(valid[0][1])

        self.table.currentCellChanged.connect(self.on_row_changed)

    def on_row_changed(self, row: int, *_):
        if 0 <= row < len(self._paths):
            self.viewer.load_path(self._paths[row])


