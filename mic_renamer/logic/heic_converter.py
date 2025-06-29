from __future__ import annotations

from pathlib import Path

from PIL import Image
from pillow_heif import register_heif_opener

from ..utils.i18n import tr

"""Utilities for converting HEIC images to common formats."""

register_heif_opener()


def heic_to_jpeg(heic_path: Path) -> Path:
    """Convert a HEIC file to JPEG and return the new path."""
    jpeg_path = heic_path.with_suffix(".jpeg")
    try:
        img = Image.open(heic_path)
        img.save(jpeg_path, "jpeg")
    except Exception as e:
        raise OSError(tr("heic_conversion_error").format(path=heic_path, error=e)) from e
    return jpeg_path


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
        exif_data = img.info.get("exif")
    except Exception:
        return path
    img = img.convert("RGB")
    dest = src.with_suffix(".jpg")
    try:
        if exif_data:
            img.save(dest, format="JPEG", exif=exif_data)
        else:
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
        exif_data = img.info.get("exif")
    except Exception:
        return path

    has_alpha = "A" in img.getbands()
    if has_alpha:
        dest = src.with_suffix(".png")
        if exif_data:
            img.save(dest, format="PNG", exif=exif_data)
        else:
            img.save(dest, format="PNG")
    else:
        img = img.convert("RGB")
        dest = src.with_suffix(".jpg")
        if exif_data:
            img.save(dest, format="JPEG", exif=exif_data)
        else:
            img.save(dest, format="JPEG")
    img.close()
    try:
        src.unlink()
    except Exception:
        pass
    return str(dest)
