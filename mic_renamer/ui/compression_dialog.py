from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QDialogButtonBox,
    QProgressDialog,
    QLabel,
)
import os
import tempfile
import shutil
from pathlib import Path

from ..logic.image_compressor import ImageCompressor
from ..utils.i18n import tr
from .. import config_manager
from ..utils.state_manager import StateManager
from .panels.media_viewer import MediaViewer
from ..utils.workers import Worker
from PySide6.QtCore import QThread, Qt


class CompressionDialog(QDialog):
    """Dialog showing compression progress and results."""

    def __init__(
        self,
        rows_and_paths: list[tuple[int, str]],
        convert_heic: bool,
        parent=None,
        state_manager: StateManager | None = None,
    ):
        super().__init__(parent)
        self.state_manager = state_manager
        self.setWindowTitle(tr("compression_window_title"))
        self.results: list[tuple[int, str, str, int, int]] = []
        self.final_results: list[tuple[int, str, int, int]] = []
        self._paths: list[str] = []
        self._tmpdir = tempfile.TemporaryDirectory()
        layout = QVBoxLayout(self)

        if self.state_manager:
            width = self.state_manager.get("compression_width", 800)
            height = self.state_manager.get("compression_height", 600)
        else:
            width, height = 800, 600
        self.resize(width, height)

        self.viewer = MediaViewer()
        layout.addWidget(self.viewer)
        layout.addWidget(QLabel(tr("compression_ok_info")))

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
        # allow interaction with the dialog while running
        self.progress.setWindowModality(Qt.NonModal)
        self.progress.setMinimumDuration(200)
        self.progress.setValue(0)

        worker = Worker(self._compress_item, valid)
        self._thread = QThread()
        worker.moveToThread(self._thread)
        self._worker = worker
        self._thread.started.connect(worker.run, Qt.QueuedConnection)
        worker.progress.connect(self._on_progress, Qt.QueuedConnection)
        worker.finished.connect(self._on_finished, Qt.QueuedConnection)
        worker.finished.connect(self._thread.quit, Qt.QueuedConnection)
        self._thread.finished.connect(self._thread.deleteLater, Qt.QueuedConnection)
        self._thread.finished.connect(self._on_thread_finished, Qt.QueuedConnection)
        worker.finished.connect(worker.deleteLater, Qt.QueuedConnection)
        # Canceling the progress should reject the compression dialog
        self.progress.canceled.connect(self.reject, Qt.QueuedConnection)
        self._thread.start()

        self.table.currentCellChanged.connect(self.on_row_changed)

    def _compress_item(self, item: tuple[int, str]):
        row, path = item
        old_size = os.path.getsize(path)
        dest_name = f"{row}_{os.path.basename(path)}"
        dest = os.path.join(self._tmpdir.name, dest_name)
        new_path, new_size, reduction = self._compressor.compress(
            path,
            self._convert_heic,
            dest_path=dest,
        )
        return row, path, new_path, old_size, new_size, reduction

    def _on_progress(self, done: int, total: int, item: tuple[int, str]):
        row, path = item
        self.progress.setValue(done)
        self.viewer.load_path(path)

    def _on_finished(self, results: list):
        self.progress.close()
        self._btn_ok.setEnabled(True)
        self.table.setRowCount(len(results))
        for idx, res in enumerate(results):
            row, orig, preview, old_size, new_size, reduction = res
            self.table.setItem(idx, 0, QTableWidgetItem(os.path.basename(orig)))
            self.table.setItem(idx, 1, QTableWidgetItem(f"{old_size // 1024} KB"))
            self.table.setItem(idx, 2, QTableWidgetItem(f"{new_size // 1024} KB"))
            self.table.setItem(idx, 3, QTableWidgetItem(f"{reduction}%"))
            self.results.append((row, orig, preview, old_size, new_size))
            self._paths.append(preview)
        if self.table.rowCount() > 0:
            self.table.selectRow(0)
            self.viewer.load_path(self._paths[0])
        self._worker = None

    def on_row_changed(self, row: int, *_):
        if 0 <= row < len(self._paths):
            self.viewer.load_path(self._paths[row])

    def _on_thread_finished(self) -> None:
        """Reset worker and thread references when the thread ends."""
        self._thread = None
        self._worker = None

    def _cleanup_thread(self) -> None:
        """Stop and wait for the worker thread if it is still running."""
        if self._thread and self._thread.isRunning():
            if self._worker:
                self._worker.stop()
            self._thread.quit()
            self._thread.wait()

    def accept(self) -> None:
        for row, orig, preview, old_size, new_size in self.results:
            final_path = orig
            if Path(preview).suffix != Path(orig).suffix:
                final_path = str(Path(orig).with_suffix(Path(preview).suffix))
                os.remove(orig)
            shutil.move(preview, final_path)
            self.final_results.append((row, final_path, old_size, new_size))
        self._cleanup_thread()
        self._tmpdir.cleanup()
        self.progress.close()
        super().accept()

    def reject(self) -> None:
        if self._worker:
            self._worker.stop()
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()
        self._tmpdir.cleanup()
        self.progress.close()
        super().reject()

    def closeEvent(self, event):
        if self._worker:
            self._worker.stop()
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()
        self._tmpdir.cleanup()
        self.progress.close()
        if self.state_manager:
            self.state_manager.set("compression_width", self.width())
            self.state_manager.set("compression_height", self.height())
            self.state_manager.save()
        super().closeEvent(event)


