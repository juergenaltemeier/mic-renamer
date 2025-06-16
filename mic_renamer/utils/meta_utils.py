"""Utilities for reading metadata from files."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PIL import Image, ExifTags


def get_capture_date(path: str | Path, date_format: str = "%y%m%d") -> str:
    """Return the capture date of an image or video if available.

    Falls back to the file's modification time when no metadata date is found.
    """
    file_path = Path(path)
    try:
        img = Image.open(file_path)
        exif = img._getexif() or {}
        tag_map = {ExifTags.TAGS.get(k): v for k, v in exif.items()}
        dt = tag_map.get("DateTimeOriginal") or tag_map.get("DateTime")
        if dt:
            try:
                dt_obj = datetime.strptime(str(dt), "%Y:%m:%d %H:%M:%S")
                return dt_obj.strftime(date_format)
            except Exception:
                pass
    except Exception:
        pass
    try:
        ts = file_path.stat().st_mtime
        return datetime.fromtimestamp(ts).strftime(date_format)
    except Exception:
        return datetime.now().strftime(date_format)
