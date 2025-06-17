"""Manage undo history for rename operations."""
from __future__ import annotations

import os
from typing import List, Tuple


class UndoManager:
    """Keep track of rename operations to allow undo within a session."""

    def __init__(self):
        # store tuples of (row_index, original_path, new_path)
        self._history: List[Tuple[int, str, str]] = []

    def record(self, row: int, orig: str, new: str) -> None:
        """Record a successful rename operation."""
        self._history.append((row, orig, new))

    def has_history(self) -> bool:
        return bool(self._history)

    def undo_all(self) -> List[Tuple[int, str]]:
        """Undo all recorded renames in reverse order.

        Returns a list of tuples ``(row, original_path)`` for successfully
        reverted files.
        """
        undone = []
        while self._history:
            row, orig, new = self._history.pop()
            try:
                if os.path.exists(new) and os.path.abspath(orig) != os.path.abspath(new):
                    os.rename(new, orig)
                    undone.append((row, orig))
            except Exception:
                # ignore errors during undo
                pass
        return undone
