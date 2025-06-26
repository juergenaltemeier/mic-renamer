"""Threaded workers for background tasks."""
from __future__ import annotations

from typing import Callable, Iterable, Any

from PySide6.QtCore import QObject, Signal, Slot, QSize
from PySide6.QtGui import QPixmapCache, QImageReader, QImage


class Worker(QObject):
    """Generic worker processing a sequence of items in a separate thread."""

    progress = Signal(int, int, object)
    finished = Signal(list)

    def __init__(self, func: Callable[[Any], Any], items: Iterable[Any]):
        super().__init__()
        self._func = func
        self._items = list(items)
        self._stop = False
        self._results: list[Any] = []

    @Slot()
    def run(self) -> None:
        total = len(self._items)
        for idx, item in enumerate(self._items, 1):
            if self._stop:
                break
            result = self._func(item)
            self._results.append(result)
            self.progress.emit(idx, total, item)
        self.finished.emit(self._results)

    @Slot()
    def stop(self) -> None:
        self._stop = True


class PreviewLoader(QObject):
    """Load an image preview off the main thread."""

    finished = Signal(str, QImage)

    def __init__(self, path: str, target_size: QSize) -> None:
        super().__init__()
        self._path = path
        self._target_size = target_size
        self._stop = False

    @Slot()
    def run(self) -> None:
        if self._stop:
            return
        reader = QImageReader(self._path)
        reader.setAutoTransform(True)
        if self._target_size.isValid():
            reader.setScaledSize(self._target_size)
        img = reader.read()
        if not self._stop:
            self.finished.emit(self._path, img)

    def path(self) -> str:
        return self._path

    @Slot()
    def stop(self) -> None:
        self._stop = True


# keep the cache fairly small (in KB)
QPixmapCache.setCacheLimit(20480)
