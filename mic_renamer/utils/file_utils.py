# utils/file_utils.py

import os

def ensure_unique_name(candidate: str, original_path: str) -> str:
    base, ext = os.path.splitext(candidate)
    counter = 1
    new_path = candidate
    while os.path.exists(new_path) and os.path.abspath(new_path) != os.path.abspath(original_path):
        new_path = f"{base}_{counter:03d}{ext}"
        counter += 1
    return new_path

