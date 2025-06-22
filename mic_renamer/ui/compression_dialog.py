from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QDialogButtonBox,
    QProgressDialog,
)
import os

from ..logic.image_compressor import ImageCompressor
from ..utils.i18n import tr
from .. import config_manager
from .panels.media_viewer import MediaViewer
from ..utils.workers import Worker
from PySide6.QtCore import QThread, Qt


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
        self.table = QTableWidget(0, 4)
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
        self._btn_ok = btns.button(QDialogButtonBox.Ok)
        self._btn_ok.setEnabled(False)
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

        self._valid = valid
        self._compressor = compressor
        self._convert_heic = convert_heic

        self.progress = QProgressDialog(
            tr("compressing_files"),
            tr("abort"),
            0,
            len(valid),
            self,
        )
        self.progress.setWindowModality(Qt.WindowModal)
        self.progress.setMinimumDuration(200)
        self.progress.setValue(0)

        worker = Worker(self._compress_item, valid)
        self._thread = QThread(self)
        worker.moveToThread(self._thread)
        self._worker = worker
        self._thread.started.connect(worker.run)
        worker.progress.connect(self._on_progress)
        worker.finished.connect(self._on_finished)
        self.progress.canceled.connect(worker.stop)
        self._thread.start()

        self.table.currentCellChanged.connect(self.on_row_changed)

    def _compress_item(self, item: tuple[int, str]):
        row, path = item
        old_size = os.path.getsize(path)
        new_path, new_size, reduction = self._compressor.compress(path, self._convert_heic)
        return row, path, new_path, old_size, new_size, reduction

    def _on_progress(self, done: int, total: int, item: tuple[int, str]):
        row, path = item
        self.progress.setValue(done)
        self.viewer.load_path(path)

    def _on_finished(self, results: list):
        self.progress.close()
        self._thread.quit()
        self._thread.wait()
        self._worker.deleteLater()
        self._thread.deleteLater()
        self._btn_ok.setEnabled(True)
        self.table.setRowCount(len(results))
        for idx, res in enumerate(results):
            row, _orig, new_path, old_size, new_size, reduction = res
            self.table.setItem(idx, 0, QTableWidgetItem(os.path.basename(new_path)))
            self.table.setItem(idx, 1, QTableWidgetItem(f"{old_size // 1024} KB"))
            self.table.setItem(idx, 2, QTableWidgetItem(f"{new_size // 1024} KB"))
            self.table.setItem(idx, 3, QTableWidgetItem(f"{reduction}%"))
            self.results.append((row, new_path, old_size, new_size))
            self._paths.append(new_path)
        if self.table.rowCount() > 0:
            self.table.selectRow(0)
            self.viewer.load_path(self._paths[0])

    def on_row_changed(self, row: int, *_):
        if 0 <= row < len(self._paths):
            self.viewer.load_path(self._paths[row])


