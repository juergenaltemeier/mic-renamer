"""Threaded workers for background tasks."""
from __future__ import annotations

from typing import Callable, Iterable, Any

from PySide6.QtCore import QObject, Signal, Slot


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
