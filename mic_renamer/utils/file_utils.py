# utils/file_utils.py

import os


def _samefile(path1: str, path2: str) -> bool:
    """Return True if both paths refer to the same file.

    Falls back to a case-insensitive comparison on platforms lacking
    ``os.path.samefile`` (e.g. Windows without `stat` support).
    """
    try:
        return os.path.samefile(path1, path2)
    except Exception:
        return os.path.abspath(os.path.normcase(path1)) == os.path.abspath(os.path.normcase(path2))

def ensure_unique_name(candidate: str, original_path: str) -> str:
    base, ext = os.path.splitext(candidate)
    counter = 1
    new_path = candidate
    while os.path.exists(new_path) and not _samefile(new_path, original_path):
        new_path = f"{base}_{counter:03d}{ext}"
        counter += 1
    return new_path

