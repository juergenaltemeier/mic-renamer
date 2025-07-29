"""
This module defines QObject-based worker classes for performing long-running tasks
in separate threads within a PyQt/PySide application. This prevents the UI from
freezing during operations like file processing or image loading.

- `Worker`: A generic worker for processing an iterable of items with a given function.
- `PreviewLoader`: A specialized worker for loading and scaling image previews.

Both classes include mechanisms for progress reporting, completion signals, and graceful
cancellation.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Iterable, List, Tuple

from PySide6.QtCore import QObject, QSize, Qt, Signal, Slot
from PySide6.QtCore import QBuffer, QByteArray, QObject, QSize, Qt, Signal, Slot
from PySide6.QtGui import QImage, QImageReader, QPixmapCache

logger = logging.getLogger(__name__)


class Worker(QObject):
    """
    A generic worker for processing a sequence of items in a separate thread.

    Signals:
        progress (int, int, object): Emitted periodically to report progress.
                                     Arguments: (current_index, total_items, current_item).
        finished (list): Emitted when all items have been processed or the worker is stopped.
                         Argument: A list of results from processing each item.
    """

    progress = Signal(int, int, object)
    finished = Signal(list)

    def __init__(self, func: Callable[[Any], Any], items: Iterable[Any]):
        """
        Initializes the Worker.

        Args:
            func (Callable[[Any], Any]): The function to apply to each item in the `items` iterable.
                                         This function should accept one item and return a result.
            items (Iterable[Any]): An iterable (e.g., list, tuple) of items to be processed by `func`.
        """
        super().__init__()
        self._func = func
        self._items = list(items) # Convert to list to ensure consistent iteration and length checking.
        self._stop = False # Flag to signal the worker to stop processing.
        self._results: list[Any] = [] # List to store the results of processing each item.
        logger.debug(f"Worker initialized with {len(self._items)} items.")

    @Slot()
    def run(self) -> None:
        """
        Executes the worker's task, processing each item in the `_items` list.

        This method is designed to be run in a separate QThread. It iterates through
        the items, applies the `_func` to each, collects results, and emits progress
        signals. It can be gracefully stopped by setting `_stop` to True.
        """
        total = len(self._items)
        logger.info(f"Worker started processing {total} items.")
        for idx, item in enumerate(self._items, 1):
            if self._stop:
                logger.info(f"Worker stopped prematurely at item {idx}/{total}.")
                break # Exit the loop if a stop signal is received.
            try:
                result = self._func(item)
                self._results.append(result)
                # Emit progress signal: current index, total items, and the item being processed.
                self.progress.emit(idx, total, item)
                logger.debug(f"Processed item {idx}/{total}. Result: {result}")
            except Exception as e:
                # Log any errors that occur during the processing of an individual item.
                logger.error(f"Error processing item {item}: {e}")
                # Depending on requirements, could append an error indicator or skip the item.
                self._results.append(None) # Append None or a specific error object for failed items.
        
        # Emit the finished signal with all collected results.
        self.finished.emit(self._results)
        logger.info(f"Worker finished. Processed {len(self._results)} items.")

    @Slot()
    def stop(self) -> None:
        """
        Signals the worker to stop its current processing gracefully.

        The worker will complete the current item being processed and then exit its loop.
        """
        self._stop = True
        logger.info("Worker stop signal received.")


class PreviewLoader(QObject):
    """
    A specialized worker for loading and scaling an image preview in a separate thread.

    This prevents the UI from freezing when loading large image files for display.

    Signals:
        finished (str, QImage): Emitted when the image loading and scaling is complete.
                                Arguments: (image_path, loaded_qimage).
    """

    finished = Signal(str, QByteArray)

    def __init__(self, path: str, target_size: QSize) -> None:
        """
        Initializes the PreviewLoader.

        Args:
            path (str): The absolute path to the image file to load.
            target_size (QSize): The target dimensions (width and height) for the preview image.
                                 The image will be scaled to fit within these dimensions while
                                 maintaining its aspect ratio.
        """
        super().__init__()
        self._path = path
        self._target_size = target_size
        self._stop = False # Flag to signal the loader to stop.
        logger.debug(f"PreviewLoader initialized for path: {self._path}, target size: {self._target_size.width()}x{self._target_size.height()}")

    @Slot()
    def run(self) -> None:
        """
        Executes the image loading and scaling task.

        This method is designed to be run in a separate QThread. It attempts to load
        the image, scales it to the target size while maintaining aspect ratio, and
        then emits the `finished` signal with the loaded QImage. It can be stopped
        prematurely by setting `_stop` to True.
        """
        if self._stop:
            logger.info(f"PreviewLoader for {self._path} stopped before starting.")
            return

        img = QImage() # Initialize an empty QImage for error cases.
        try:
            # Use QImageReader for efficient image loading, especially for large files.
            reader = QImageReader(self._path)
            if not reader.canRead():
                logger.warning(f"QImageReader cannot read image file: {self._path}. Format unsupported or file corrupted.")
                self.finished.emit(self._path, img) # Emit empty QImage on failure.
                return

            # Enable auto-transformation (e.g., for EXIF orientation).
            reader.setAutoTransform(True)
            img = reader.read()

            if img.isNull():
                logger.warning(f"QImageReader read an invalid image from {self._path}. It might be corrupted.")
                self.finished.emit(self._path, QImage()) # Emit empty QImage on read failure.
                return

            # If not stopped and target size is valid, scale the image.
            if not self._stop and self._target_size.isValid() and not img.isNull():
                # Scale the image, keeping aspect ratio and using smooth transformation for quality.
                scaled_img = img.scaled(
                    self._target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                logger.debug(f"Scaled image {self._path} from {img.width()}x{img.height()} to {scaled_img.width()}x{scaled_img.height()}")
                img = scaled_img

            # Convert QImage to QByteArray (PNG format)
            byte_array = QByteArray()
            buffer = QBuffer(byte_array)
            buffer.open(QBuffer.WriteOnly)
            img.save(buffer, "PNG") # Save as PNG to preserve quality
            buffer.close()
            
            # Emit the finished signal with the path and the QByteArray
            if not self._stop:
                self.finished.emit(self._path, byte_array)
                logger.info(f"PreviewLoader finished for {self._path}.")
            else:
                logger.info(f"PreviewLoader for {self._path} stopped before emitting finished signal.")
            
        except Exception as e:
            # Catch any errors during image loading or processing.
            logger.error(f"Error loading or scaling preview for {self._path}: {e}")
            # Emit empty QByteArray on error
            if not self._stop: # Only emit on error if not stopped
                self.finished.emit(self._path, QByteArray())
        
    def path(self) -> str:
        """
        Returns the path of the image being loaded by this worker.

        Returns:
            str: The absolute path to the image file.
        """
        return self._path

    @Slot()
    def stop(self) -> None:
        """
        Signals the preview loader to stop its operation gracefully.

        The loader will cease processing and will not emit the `finished` signal
        if stopped before completion.
        """
        self._stop = True
        logger.info(f"PreviewLoader stop signal received for {self._path}.")


# Set a reasonable cache limit for QPixmapCache to manage memory usage for image previews.
# The value is in kilobytes (KB). 20480 KB = 20 MB.
QPixmapCache.setCacheLimit(10240)
logger.info(f"QPixmapCache limit set to {QPixmapCache.cacheLimit()} KB.")

