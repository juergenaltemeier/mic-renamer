"""
This module provides the `UndoManager` class, which is responsible for tracking and managing
the history of file rename operations. This allows users to revert (undo) previously
performed renaming actions within the current application session. Robust error handling
is implemented for file system operations during the undo process.
"""
from __future__ import annotations

import os
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class UndoManager:
    """
    Manages the history of rename operations to allow undo functionality within a session.

    Each successful rename operation is recorded, storing the original and new file paths
    along with the associated row index from the UI (if applicable).
    """

    def __init__(self):
        """
        Initializes a new UndoManager instance.

        The undo history is stored as a list of tuples, where each tuple contains:
        (row_index: int, original_path: str, new_path: str).
        """
        self._history: List[Tuple[int, str, str]] = []
        logger.info("UndoManager initialized.")

    def record(self, row: int, orig: str, new: str) -> None:
        """
        Records a successful file rename operation into the undo history.

        Args:
            row (int): The row index associated with the file in the UI, useful for feedback.
            orig (str): The absolute path of the original file before renaming.
            new (str): The absolute path of the file after renaming.
        """
        # Append the details of the rename operation to the history list.
        self._history.append((row, orig, new))
        logger.debug(f"Recorded rename: row={row}, original='{orig}', new='{new}'")

    def has_history(self) -> bool:
        """
        Checks if there are any rename operations recorded in the undo history.

        Returns:
            bool: True if the history is not empty, False otherwise.
        """
        return bool(self._history)

    def undo_all(self) -> List[Tuple[int, str]]:
        """
        Undoes all recorded rename operations in reverse order of their recording.

        For each operation, it attempts to rename the file back from its new path
        to its original path. Errors during individual undo operations are caught
        and logged, but the process continues for other files.

        Returns:
            List[Tuple[int, str]]: A list of tuples, where each tuple contains
                                   (row_index, original_path) for files that were
                                   successfully reverted.
        """
        undone_successfully: List[Tuple[int, str]] = []
        # Process history in reverse order (LIFO - Last In, First Out).
        while self._history:
            row, orig, new = self._history.pop() # Get the last recorded operation
            logger.info(f"Attempting to undo rename: new='{new}' to original='{orig}' (row={row})")
            try:
                # Check if the new file path still exists and if the paths are actually different.
                # os.path.abspath is used to normalize paths for comparison, especially on Windows.
                if os.path.exists(new) and os.path.abspath(orig) != os.path.abspath(new):
                    # Perform the rename operation to revert the file.
                    os.rename(new, orig)
                    undone_successfully.append((row, orig))
                    logger.info(f"Successfully undid rename for row {row}: '{new}' -> '{orig}'")
                elif not os.path.exists(new):
                    logger.warning(f"Cannot undo rename for row {row}. New path '{new}' does not exist.")
                else:
                    logger.info(f"Skipping undo for row {row}. Original and new paths are identical: '{orig}'.")
            except OSError as e:
                # Catch OS-level errors (e.g., permission denied, file in use).
                logger.error(f"OS Error during undo for row {row} ('{new}' -> '{orig}'): {e}")
            except Exception as e:
                # Catch any other unexpected errors during the undo process.
                logger.error(f"An unexpected error occurred during undo for row {row} ('{new}' -> '{orig}'): {e}")
                # Continue processing other history items even if one fails.
        
        if not undone_successfully:
            logger.info("No rename operations were successfully undone.")
        else:
            logger.info(f"Successfully undid {len(undone_successfully)} rename operations.")
        return undone_successfully
