from __future__ import annotations

"""Utilities for converting HEIC images to common formats."""

from pathlib import Path
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()


def convert_to_jpeg(path: str) -> str:
    """Convert any image to JPEG.

    Returns the path to the converted image. If conversion fails or the
    image is already a JPEG, the original path is returned.
    """
    src = Path(path)
    if src.suffix.lower() in {".jpg", ".jpeg"}:
        return path
    try:
        img = Image.open(src)
    except Exception:
        return path
    img = img.convert("RGB")
    dest = src.with_suffix(".jpg")
    try:
        img.save(dest, format="JPEG")
    except Exception:
        img.close()
        return path
    img.close()
    try:
        src.unlink()
    except Exception:
        pass
    return str(dest)


def convert_heic(path: str) -> str:
    """Convert a HEIC image to JPEG or PNG depending on transparency.

    Returns the path to the converted image. If ``path`` is not a HEIC image
    or conversion fails, the original path is returned.
    """
    src = Path(path)
    if src.suffix.lower() != ".heic":
        return path
    try:
        img = Image.open(src)
    except Exception:
        return path

    has_alpha = "A" in img.getbands()
    if has_alpha:
        dest = src.with_suffix(".png")
        img.save(dest, format="PNG")
    else:
        img = img.convert("RGB")
        dest = src.with_suffix(".jpg")
        img.save(dest, format="JPEG")
    img.close()
    try:
        src.unlink()
    except Exception:
        pass
    return str(dest)
