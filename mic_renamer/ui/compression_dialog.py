from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from PySide6.QtCore import QThread, Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .. import config_manager
from ..logic.image_compressor import ImageCompressor
from ..utils.i18n import tr
from ..utils.state_manager import StateManager
from ..utils.workers import Worker
from .panels.media_viewer import MediaViewer


class CompressionDialog(QDialog):
    """A dialog for compressing images, showing progress and results."""

    def __init__(
        self,
        rows_and_paths: list[tuple[int, str]],
        convert_heic: bool,
        parent=None,
        state_manager: StateManager | None = None,
    ):
        """
        Initializes the CompressionDialog.

        Args:
            rows_and_paths: A list of tuples, where each tuple contains the
                            row index and the file path.
            convert_heic: A boolean indicating whether to convert HEIC files.
            parent: The parent widget.
            state_manager: An optional StateManager instance.
        """
        super().__init__(parent)
        self.state_manager = state_manager
        self.setWindowTitle(tr("compression_window_title"))
        self.final_results: list[tuple[int, str, int, int]] = []
        self._results: list[tuple[int, Path, Path, int, int]] = []
        self._tmpdir = tempfile.TemporaryDirectory()

        self._setup_ui()
        self._load_state()

        valid_paths = self._filter_valid_paths(rows_and_paths)
        compressor = self._create_compressor()

        self._start_compression_worker(valid_paths, compressor, convert_heic)

    def _setup_ui(self):
        """Sets up the user interface of the dialog."""
        layout = QVBoxLayout(self)
        self.viewer = MediaViewer()
        layout.addWidget(self.viewer)
        layout.addWidget(QLabel(tr("compression_ok_info")))

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

        self.table.currentCellChanged.connect(self.on_row_changed)

    def _load_state(self):
        """Loads the dialog's size from the state manager."""
        if self.state_manager:
            width = self.state_manager.get("compression_width", 800)
            height = self.state_manager.get("compression_height", 600)
            self.resize(width, height)

    def _filter_valid_paths(self, rows_and_paths: list[tuple[int, str]]) -> list[tuple[int, Path]]:
        """Filters the input list to include only existing files."""
        valid = []
        for row, path_str in rows_and_paths:
            path = Path(path_str)
            if path.is_file():
                valid.append((row, path))
            else:
                self.parent().logger.warning(f"File not found: {path_str}")
        return valid

    def _create_compressor(self) -> ImageCompressor:
        """Creates an ImageCompressor instance from the configuration."""
        cfg = config_manager.load()
        return ImageCompressor(
            max_size_kb=cfg.get("compression_max_size_kb", 2048),
            quality=cfg.get("compression_quality", 95),
            reduce_resolution=cfg.get("compression_reduce_resolution", True),
            resize_only=cfg.get("compression_resize_only", False),
            max_width=cfg.get("compression_max_width", 0) or None,
            max_height=cfg.get("compression_max_height", 0) or None,
        )

    def _start_compression_worker(
        """
This module defines the `CompressionDialog` class, a PyQt/PySide dialog for managing
image compression tasks. It provides a user interface to display compression progress,
preview compressed images, and apply the changes. The compression itself is performed
in a separate thread to keep the UI responsive, and robust error handling is included
for file operations and worker management.
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
import logging

from PySide6.QtCore import QThread, Qt, QSize
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .. import config_manager
from ..logic.image_compressor import ImageCompressor
from ..utils.i18n import tr
from ..utils.state_manager import StateManager
from ..utils.workers import Worker
from .panels.media_viewer import MediaViewer

logger = logging.getLogger(__name__)


class CompressionDialog(QDialog):
    """
    A dialog for compressing images, showing progress, preview, and results.

    It orchestrates the compression process using a background worker to maintain
    UI responsiveness and allows users to review and apply or discard changes.
    """

    def __init__(
        self,
        rows_and_paths: list[tuple[int, str]],
        convert_heic: bool,
        parent=None,
        state_manager: StateManager | None = None,
    ):
        """
        Initializes the CompressionDialog.

        Args:
            rows_and_paths (list[tuple[int, str]]): A list of tuples, where each tuple contains
                                                    the row index from the main table and the
                                                    absolute file path of the image to compress.
            convert_heic (bool): A boolean flag indicating whether HEIC files should be
                                 converted to JPEG during compression.
            parent (QWidget, optional): The parent widget for this dialog. Defaults to None.
            state_manager (StateManager | None): An optional StateManager instance for
                                                 persisting dialog size and position. Defaults to None.
        """
        super().__init__(parent)
        self.state_manager = state_manager
        self.setWindowTitle(tr("compression_window_title"))
        
        # Stores the final results after successful compression and application.
        # Format: (original_row_index, final_path_after_compression, original_size, new_size)
        self.final_results: list[tuple[int, str, int, int]] = []
        
        # Stores intermediate results from the worker before applying changes.
        # Format: (original_row_index, original_path, preview_path_in_tmp, original_size, new_size)
        self._results: list[tuple[int, Path, Path, int, int]] = []
        
        # Create a temporary directory to store compressed preview files.
        try:
            self._tmpdir = tempfile.TemporaryDirectory()
            logger.info(f"Created temporary directory for compression previews: {self._tmpdir.name}")
        except Exception as e:
            logger.critical(f"Failed to create temporary directory: {e}. Compression dialog may not function.")
            QMessageBox.critical(self, tr("error"), f"Failed to create temporary directory: {e}")
            self.reject() # Reject the dialog if temp directory cannot be created.
            return

        self._setup_ui()
        self._load_state()

        # Filter out non-existent files before starting compression.
        valid_paths = self._filter_valid_paths(rows_and_paths)
        if not valid_paths:
            QMessageBox.information(self, tr("no_files"), tr("no_files_msg"))
            self.reject()
            return

        # Create the ImageCompressor instance based on current configuration.
        compressor = self._create_compressor()

        # Start the background worker to perform compression.
        self._start_compression_worker(valid_paths, compressor, convert_heic)

    def _setup_ui(self) -> None:
        """
        Sets up the user interface elements of the compression dialog.

        This includes the media viewer for previews, a table to display compression
        results, and standard OK/Cancel buttons.
        """
        layout = QVBoxLayout(self)
        
        # MediaViewer to display image previews.
        self.viewer = MediaViewer()
        layout.addWidget(self.viewer)
        
        # Informational label for the user.
        layout.addWidget(QLabel(tr("compression_ok_info")))

        # Table to display compression results: File, Old Size, New Size, Reduction.
        self.table = QTableWidget(0, 4) # 0 rows initially, 4 columns.
        self.table.setHorizontalHeaderLabels([
            tr("file"),
            tr("old_size"),
            tr("new_size"),
            tr("reduction"),
        ])
        self.table.verticalHeader().setVisible(False) # Hide row numbers.
        self.table.setEditTriggers(QTableWidget.NoEditTriggers) # Make table read-only.
        layout.addWidget(self.table)

        # Standard OK and Cancel buttons.
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(btns)
        self._btn_ok = btns.button(QDialogButtonBox.Ok)
        self._btn_ok.setEnabled(False) # Disable OK button until compression finishes.
        
        # Connect button signals to dialog slots.
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

        # Connect table selection change to update the media viewer.
        self.table.currentCellChanged.connect(self.on_row_changed)
        logger.debug("CompressionDialog UI setup complete.")

    def _load_state(self) -> None:
        """
        Loads the dialog's size and position from the state manager.
        """
        if self.state_manager:
            width = self.state_manager.get("compression_width", 800)
            height = self.state_manager.get("compression_height", 600)
            self.resize(width, height)
            logger.debug(f"Loaded dialog size from state: {width}x{height}")
        else:
            logger.debug("No StateManager available to load dialog size.")

    def _filter_valid_paths(self, rows_and_paths: list[tuple[int, str]]) -> list[tuple[int, Path]]:
        """
        Filters the input list of paths to include only existing files.

        Args:
            rows_and_paths (list[tuple[int, str]]): List of (row_index, file_path_string).

        Returns:
            list[tuple[int, Path]]: A filtered list of (row_index, pathlib.Path) for existing files.
        """
        valid_files = []
        for row, path_str in rows_and_paths:
            path = Path(path_str)
            if path.is_file():
                valid_files.append((row, path))
            else:
                logger.warning(f"Skipping non-existent file for compression: {path_str}")
                # Optionally, inform the user or log this more prominently.
        logger.info(f"Filtered {len(rows_and_paths)} paths to {len(valid_files)} valid files.")
        return valid_files

    def _create_compressor(self) -> ImageCompressor:
        """
        Creates an `ImageCompressor` instance based on the current application configuration.

        Returns:
            ImageCompressor: An initialized ImageCompressor object.
        """
        cfg = config_manager.load()
        compressor = ImageCompressor(
            max_size_kb=cfg.get("compression_max_size_kb", 2048), # Default to 2MB
            quality=cfg.get("compression_quality", 95),
            reduce_resolution=cfg.get("compression_reduce_resolution", True),
            resize_only=cfg.get("compression_resize_only", False),
            max_width=cfg.get("compression_max_width", 0) or None, # 0 means no limit
            max_height=cfg.get("compression_max_height", 0) or None, # 0 means no limit
        )
        logger.debug("ImageCompressor created with current config.")
        return compressor

    def _start_compression_worker(
        self, valid_paths: list[tuple[int, Path]], compressor: ImageCompressor, convert_heic: bool
    ) -> None:
        """
        Initializes and starts a background worker thread for image compression.

        Args:
            valid_paths (list[tuple[int, Path]]): List of (row_index, Path) for files to compress.
            compressor (ImageCompressor): The compressor instance to use.
            convert_heic (bool): Whether to convert HEIC files during compression.
        """
        # Setup progress dialog.
        self.progress = QProgressDialog(
            tr("compressing_files"), # Text displayed in the progress dialog.
            tr("abort"), # Text for the cancel button.
            0,
            len(valid_paths),
            self,
        )
        self.progress.setWindowModality(Qt.NonModal) # Allows interaction with other windows.
        self.progress.setMinimumDuration(200) # Show progress dialog only after 200ms.
        self.progress.setValue(0) # Initialize progress to 0.
        self.progress.setWindowTitle(tr("compression_window_title"))

        self._compressor = compressor
        self._convert_heic = convert_heic

        # Create a Worker instance, passing the compression function and items.
        worker = Worker(self._compress_item, valid_paths)
        self._thread = QThread() # Create a new QThread for the worker.
        worker.moveToThread(self._thread) # Move the worker object to the new thread.
        self._worker = worker # Keep a reference to the worker.
        
        # Connect signals and slots.
        self._thread.started.connect(worker.run) # When thread starts, run the worker.
        worker.progress.connect(self._on_progress) # Update UI on progress.
        worker.finished.connect(self._on_finished) # Handle completion.
        worker.finished.connect(self._thread.quit) # Quit thread when worker finishes.
        worker.finished.connect(worker.deleteLater) # Clean up worker object.
        self._thread.finished.connect(self._thread.deleteLater) # Clean up thread object.
        self.progress.canceled.connect(worker.stop) # Allow user to cancel the worker.
        
        # Start the thread.
        self._thread.start()
        logger.info(f"Compression worker started for {len(valid_paths)} files.")

    def _compress_item(self, item: tuple[int, Path]) -> tuple[int, Path, Path, int, int, int]:
        """
        Compresses a single image file.

        This method is executed by the background worker. It performs the actual
        compression using the `ImageCompressor` and handles potential errors.

        Args:
            item (tuple[int, Path]): A tuple containing the original row index and the
                                     Path object of the file to compress.

        Returns:
            tuple[int, Path, Path, int, int, int]: A tuple containing:
                - Original row index (int)
                - Original file Path (Path)
                - Path to the compressed preview file in the temporary directory (Path)
                - Original file size in bytes (int)
                - New file size in bytes after compression (int)
                - Percentage reduction (int)
            Returns (row, original_path, original_path, 0, 0, 0) if compression fails.
        """
        row, path = item
        try:
            old_size = path.stat().st_size
            # Create a unique destination name for the compressed preview in the temporary directory.
            # Using row_index_filename ensures uniqueness and traceability.
            dest_name = f"{row}_{path.name}"
            dest_path_in_tmp = Path(self._tmpdir.name) / dest_name
            
            # Perform the compression.
            new_path_str, new_size, reduction = self._compressor.compress(
                str(path), self._convert_heic, dest_path=str(dest_path_in_tmp)
            )
            # Convert the returned new_path_str back to Path object.
            new_path_obj = Path(new_path_str)
            logger.debug(f"Compressed {path.name}: Old size {old_size}B, New size {new_size}B, Reduction {reduction}%")
            return row, path, new_path_obj, old_size, new_size, reduction
        except Exception as e:
            logger.error(f"Failed to compress {path}: {e}")
            # Return original path and zero sizes/reduction on failure.
            return row, path, path, 0, 0, 0

    def _on_progress(self, done: int, total: int, item: tuple[int, Path]) -> None:
        """
        Slot to update the progress dialog and media viewer during compression.

        Args:
            done (int): Number of items processed so far.
            total (int): Total number of items to process.
            item (tuple[int, Path]): The current item being processed (row_index, original_path).
        """
        row, path = item
        self.progress.setValue(done) # Update progress dialog value.
        self.viewer.load_path(str(path)) # Load the original image for preview during progress.
        logger.debug(f"Compression progress: {done}/{total} for {path.name}")

    def _on_finished(self, results: list) -> None:
        """
        Slot to handle the completion of the compression worker thread.

        It closes the progress dialog, enables the OK button, populates the results
        table, and displays the first compressed image preview.

        Args:
            results (list): A list of results from the `_compress_item` function for each file.
        """
        self.progress.close() # Close the progress dialog.
        self._btn_ok.setEnabled(True) # Enable the OK button to allow applying changes.
        
        self.table.setRowCount(len(results)) # Set the number of rows in the table.
        for idx, res in enumerate(results):
            # Unpack the result tuple.
            row, orig_path, preview_path, old_size, new_size, reduction = res
            
            # Store the relevant parts of the result for later use in `accept`.
            self._results.append((row, orig_path, preview_path, old_size, new_size))

            # Populate the table with compression details.
            self.table.setItem(idx, 0, QTableWidgetItem(orig_path.name)) # File name
            self.table.setItem(idx, 1, QTableWidgetItem(f"{old_size // 1024} KB")) # Old size in KB
            self.table.setItem(idx, 2, QTableWidgetItem(f"{new_size // 1024} KB")) # New size in KB
            self.table.setItem(idx, 3, QTableWidgetItem(f"{reduction}%")) # Reduction percentage
            logger.debug(f"Table row {idx} populated for {orig_path.name}")

        # Select the first row and display its preview if there are results.
        if self.table.rowCount() > 0:
            self.table.selectRow(0)
            self.on_row_changed(0) # Manually trigger the preview update for the first row.

        self._worker = None # Clear worker reference.
        logger.info("Compression worker finished and results displayed.")

    def on_row_changed(self, row: int, *_) -> None:
        """
        Slot to update the media viewer when the selected row in the table changes.

        Args:
            row (int): The index of the newly selected row.
            *_ : Placeholder for additional arguments from the signal (e.g., old_row, old_column).
        """
        if 0 <= row < len(self._results):
            # Load the preview image from the temporary path associated with the selected row.
            self.viewer.load_path(str(self._results[row][2]))
            logger.debug(f"Preview updated for row {row}: {self._results[row][2].name}")
        else:
            logger.warning(f"Attempted to change to invalid row: {row}")

    def accept(self) -> None:
        """
        Overrides the QDialog.accept() method.

        This method is called when the user clicks the OK button. It applies the
        compressed files by moving them from the temporary directory to their
        original locations (or new locations if extension changed). It also updates
        `final_results` and handles file system errors.
        """
        logger.info("Applying compression results...")
        try:
            for row, orig_path, preview_path, old_size, new_size in self._results:
                # Determine the final destination path.
                final_path = orig_path
                # If the extension changed (e.g., HEIC to JPG), update the final path and delete original.
                if preview_path.suffix.lower() != orig_path.suffix.lower():
                    final_path = orig_path.with_suffix(preview_path.suffix)
                    try:
                        orig_path.unlink() # Delete the original file.
                        logger.debug(f"Deleted original file {orig_path} after extension change.")
                    except OSError as e:
                        logger.error(f"Failed to delete original file {orig_path} during apply: {e}")
                        # Decide whether to continue or raise. For now, continue.
                
                # Move the compressed file from the temporary location to its final destination.
                shutil.move(str(preview_path), str(final_path))
                self.final_results.append((row, str(final_path), old_size, new_size))
                logger.debug(f"Moved {preview_path.name} to {final_path.name}")
            
            logger.info("Compression results applied successfully.")
            super().accept() # Call base class accept to close the dialog.
        except (IOError, OSError) as e:
            logger.error(f"Failed to apply compression results: {e}")
            QMessageBox.warning(self, tr("error"), tr("compression_apply_failed").format(error=e))
            super().reject() # Reject the dialog on critical error.
        except Exception as e:
            logger.error(f"An unexpected error occurred while applying compression results: {e}")
            QMessageBox.warning(self, tr("error"), f"An unexpected error occurred: {e}")
            super().reject()
        finally:
            self._cleanup() # Ensure temporary directory is cleaned up.

    def reject(self) -> None:
        """
        Overrides the QDialog.reject() method.

        This method is called when the user clicks the Cancel button or closes the dialog
        without applying changes. It stops any running worker and cleans up temporary files.
        """
        logger.info("Compression dialog rejected. Cleaning up...")
        # If a worker is still running, stop it gracefully.
        if hasattr(self, "_worker") and self._worker:
            self._worker.stop()
            # Optionally, wait for the worker thread to finish if immediate cleanup is critical.
            # self._thread.wait()
        self._cleanup() # Clean up the temporary directory.
        super().reject() # Call base class reject to close the dialog.

    def closeEvent(self, event) -> None:
        """
        Handles the dialog closing event.

        Ensures that any running worker is stopped and temporary files are cleaned up.
        Also saves the dialog's size to the state manager.

        Args:
            event (QCloseEvent): The close event.
        """
        logger.info("Compression dialog closing.")
        # Stop worker if it's still active.
        if hasattr(self, "_worker") and self._worker:
            self._worker.stop()
            # self._thread.wait() # Consider waiting if cleanup must happen before dialog closes.
        self._cleanup() # Clean up temporary directory.
        
        # Save dialog size to state manager.
        if self.state_manager:
            self.state_manager.set("compression_width", self.width())
            self.state_manager.set("compression_height", self.height())
            self.state_manager.save()
            logger.debug("Saved dialog size to state.")
        else:
            logger.debug("No StateManager available to save dialog size.")
            
        super().closeEvent(event) # Call base class closeEvent.

    def _cleanup(self) -> None:
        """
        Cleans up the temporary directory created for storing compressed preview files.

        This method is called when the dialog is closed or its actions are completed.
        """
        if hasattr(self, "_tmpdir") and self._tmpdir:
            try:
                self._tmpdir.cleanup()
                logger.info(f"Temporary directory {self._tmpdir.name} cleaned up.")
            except Exception as e:
                logger.error(f"Failed to cleanup temporary directory {self._tmpdir.name}: {e}")
        else:
            logger.debug("No temporary directory to clean up.")
        self.progress = QProgressDialog(
            tr("compressing_files"),
            tr("abort"),
            0,
            len(valid_paths),
            self,
        )
        self.progress.setWindowModality(Qt.NonModal)
        self.progress.setMinimumDuration(200)
        self.progress.setValue(0)

        self._compressor = compressor
        self._convert_heic = convert_heic

        worker = Worker(self._compress_item, valid_paths)
        self._thread = QThread()
        worker.moveToThread(self._thread)
        self._worker = worker
        self._thread.started.connect(worker.run)
        worker.progress.connect(self._on_progress)
        worker.finished.connect(self._on_finished)
        worker.finished.connect(self._thread.quit)
        worker.finished.connect(worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self.progress.canceled.connect(worker.stop)
        self._thread.start()

    def _compress_item(self, item: tuple[int, Path]) -> tuple[int, Path, Path, int, int, int]:
        """Compresses a single item."""
        row, path = item
        try:
            old_size = path.stat().st_size
            dest_name = f"{row}_{path.name}"
            dest = Path(self._tmpdir.name) / dest_name
            new_path, new_size, reduction = self._compressor.compress(
                str(path), self._convert_heic, dest_path=str(dest)
            )
            return row, path, Path(new_path), old_size, new_size, reduction
        except Exception as e:
            self.parent().logger.error(f"Failed to compress {path}: {e}")
            return row, path, path, 0, 0, 0

    def _on_progress(self, done: int, total: int, item: tuple[int, Path]):
        """Updates the progress dialog and viewer during compression."""
        row, path = item
        self.progress.setValue(done)
        self.viewer.load_path(str(path))

    def _on_finished(self, results: list):
        """Handles the completion of the compression worker."""
        self.progress.close()
        self._btn_ok.setEnabled(True)
        self.table.setRowCount(len(results))
        for idx, res in enumerate(results):
            row, orig, preview, old_size, new_size, reduction = res
            self.table.setItem(idx, 0, QTableWidgetItem(orig.name))
            self.table.setItem(idx, 1, QTableWidgetItem(f"{old_size // 1024} KB"))
            self.table.setItem(idx, 2, QTableWidgetItem(f"{new_size // 1024} KB"))
            self.table.setItem(idx, 3, QTableWidgetItem(f"{reduction}%"))
            self._results.append((row, orig, preview, old_size, new_size))

        if self.table.rowCount() > 0:
            self.table.selectRow(0)
            self.on_row_changed(0)

        self._worker = None

    def on_row_changed(self, row: int, *_):
        """Shows the preview for the selected row."""
        if 0 <= row < len(self._results):
            self.viewer.load_path(str(self._results[row][2]))

    def accept(self):
        """Applies the compression results."""
        try:
            for row, orig, preview, old_size, new_size in self._results:
                final_path = orig
                if preview.suffix != orig.suffix:
                    final_path = orig.with_suffix(preview.suffix)
                    orig.unlink()
                shutil.move(str(preview), str(final_path))
                self.final_results.append((row, str(final_path), old_size, new_size))
            super().accept()
        except (IOError, OSError) as e:
            self.parent().logger.error(f"Failed to apply compression results: {e}")
            QMessageBox.warning(self, tr("error"), tr("compression_apply_failed").format(error=e))
            super().reject()
        finally:
            self._cleanup()

    def reject(self):
        """Rejects the compression results and cleans up."""
        if hasattr(self, "_worker") and self._worker:
            self._worker.stop()
        self._cleanup()
        super().reject()

    def closeEvent(self, event):
        """Handles the dialog closing event."""
        if hasattr(self, "_worker") and self._worker:
            self._worker.stop()
        self._cleanup()
        if self.state_manager:
            self.state_manager.set("compression_width", self.width())
            self.state_manager.set("compression_height", self.height())
            self.state_manager.save()
        super().closeEvent(event)

    def _cleanup(self):
        """Cleans up the temporary directory."""
        try:
            self._tmpdir.cleanup()
        except Exception as e:
            self.parent().logger.error(f"Failed to cleanup temporary directory: {e}")



