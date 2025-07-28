"""
This module provides utility functions for file system operations, focusing on
path comparison and ensuring unique file names. It includes robust handling for
different operating systems and potential file system errors.
"""
from __future__ import annotations

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _samefile(path1: Path, path2: Path) -> bool:
    """
    Determines if two paths refer to the same file.

    This function attempts to use `pathlib.Path.samefile()` for robust comparison,
    which typically relies on inode numbers on Unix-like systems and file IDs on Windows.
    If `samefile()` fails (e.g., due to `OSError` on certain platforms or `AttributeError`
    if the method is not available), it falls back to a case-insensitive comparison
    of resolved absolute paths. This fallback is particularly useful for Windows
    where `os.path.samefile` might not always behave as expected or `stat` support
    might be limited in some environments.

    Args:
        path1 (Path): The first file path.
        path2 (Path): The second file path.

    Returns:
        bool: True if both paths refer to the same file, False otherwise.
    """
    try:
        # Attempt to use the robust samefile method provided by pathlib.
        return path1.samefile(path2)
    except (OSError, AttributeError) as e:
        # Log the fallback reason.
        logger.debug(f"_samefile: Falling back to resolved path comparison due to {type(e).__name__}: {e}")
        # Fallback: Compare resolved absolute paths. On Windows, this comparison is typically case-insensitive.
        try:
            return path1.resolve().lower() == path2.resolve().lower()
        except OSError as resolve_e:
            logger.error(f"_samefile: Error resolving paths {path1} or {path2}: {resolve_e}")
            return False # If paths cannot be resolved, assume they are not the same.


def ensure_unique_name(candidate: Path, original_path: Path) -> Path:
    """
    Ensures that a `candidate` file path is unique.

    If the `candidate` path already exists and is not the `original_path` of the file
    being renamed (to prevent self-collision), a counter is appended to the filename
    (e.g., `filename_001.ext`, `filename_002.ext`) until a unique path is found.

    Args:
        candidate (Path): The desired path for the file.
        original_path (Path): The original path of the file. This is used to ensure
                              that the `candidate` is not considered a conflict if it's
                              the same as the source file (e.g., when renaming in place).

    Returns:
        Path: A unique path that does not conflict with existing files or the original file.

    Raises:
        OSError: If there are persistent issues with file system access during uniqueness checks.
    """
    # If the candidate path does not exist, or if it refers to the same file as the original path,
    # then it is already unique for the purpose of renaming.
    if not candidate.exists() or _samefile(candidate, original_path):
        logger.debug(f"Candidate path '{candidate}' is unique or same as original '{original_path}'.")
        return candidate

    # If the candidate path exists and is different from the original path, we need to find a unique name.
    base, ext = candidate.stem, candidate.suffix
    counter = 1
    new_path = candidate
    
    logger.info(f"Candidate path '{candidate}' conflicts. Finding unique name...")
    # Loop until a unique path is found.
    while True:
        try:
            # Construct a new path by appending a padded counter to the base name.
            new_path = candidate.with_name(f"{base}_{counter:03d}{ext}")
            
            # Check if the newly constructed path exists and is not the original file.
            # If it doesn't exist, or if it's the original file (which means we've looped back
            # to the original file's name after some operations, though unlikely in this context),
            # then we've found a unique name.
            if not new_path.exists() or _samefile(new_path, original_path):
                logger.info(f"Found unique path: '{new_path}'")
                return new_path
            
            counter += 1
            # Add a safeguard to prevent infinite loops in extreme cases (e.g., millions of conflicts).
            if counter > 9999:
                logger.error(f"Exceeded maximum attempts to find a unique name for {candidate}. Last attempt: {new_path}")
                raise OSError(f"Failed to find a unique name for {candidate} after many attempts.")
        except OSError as e:
            logger.error(f"OS Error during unique name generation for {candidate}: {e}")
            raise # Re-raise the OSError as it indicates a serious file system issue.
        except Exception as e:
            logger.error(f"An unexpected error occurred during unique name generation for {candidate}: {e}")
            raise # Re-raise unexpected errors


