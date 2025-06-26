"""Simple image compression utilities."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
from PIL import Image
from PIL.Image import Resampling
from pillow_heif import register_heif_opener

register_heif_opener()


class ImageCompressor:
    """Compress images using Pillow."""

    def __init__(
        self,
        max_size_kb: int = 2048,
        quality: int = 95,
        reduce_resolution: bool = True,
        resize_only: bool = False,
        max_width: int | None = None,
        max_height: int | None = None,
    ) -> None:
        self.max_size = max_size_kb * 1024
        self.quality = quality
        self.reduce_resolution = reduce_resolution
        self.resize_only = resize_only
        self.max_width = max_width
        self.max_height = max_height

    def compress(
        self,
        path: str,
        convert_heic: bool = False,
        dest_path: str | None = None,
    ) -> tuple[str, int, int]:
        """Compress ``path`` optionally saving to ``dest_path``.

        If ``dest_path`` is ``None`` (default) the original file is overwritten.
        When ``dest_path`` is provided the original file is left untouched and
        the compressed image is written to that location instead.

        Returns a tuple ``(new_path, new_size, reduction_percent)``.
        ``new_path`` may differ if HEIC conversion occurs.
        """
        if not os.path.isfile(path):
            return path, 0, 0

        out_path = dest_path or path
        orig_size = os.path.getsize(path)

        # handle simple copy when no compression/conversion is required
        if orig_size <= self.max_size and not (convert_heic and path.lower().endswith(".heic")):
            if dest_path:
                shutil.copy2(path, out_path)
            return out_path, orig_size, 0

        img = Image.open(path)
        exif_data = img.info.get("exif")
        fmt = img.format
        if convert_heic and path.lower().endswith(".heic"):
            fmt = "JPEG"
            img = img.convert("RGB")
            out_path = str(Path(out_path).with_suffix(".jpg"))

        # resize according to configured max dimensions
        if self.max_width or self.max_height:
            scale = 1.0
            if self.max_width and img.width > self.max_width:
                scale = min(scale, self.max_width / img.width)
            if self.max_height and img.height > self.max_height:
                scale = min(scale, self.max_height / img.height)
            if scale < 1.0:
                new_w = int(img.width * scale)
                new_h = int(img.height * scale)
                img = img.resize((new_w, new_h), Resampling.LANCZOS)

        save_kwargs: dict[str, bool | int | bytes] = {"optimize": True}
        if fmt == "JPEG" and not self.resize_only:
            save_kwargs["quality"] = self.quality

        if exif_data:
            save_kwargs["exif"] = exif_data
        img.save(out_path, format=fmt, **save_kwargs)
        new_size = os.path.getsize(out_path)
        if self.reduce_resolution and new_size > self.max_size:
            while new_size > self.max_size and img.width > 100 and img.height > 100:
                img = img.resize((int(img.width * 0.9), int(img.height * 0.9)), Resampling.LANCZOS)
                if exif_data:
                    save_kwargs["exif"] = exif_data
                img.save(out_path, format=fmt, **save_kwargs)
                new_size = os.path.getsize(out_path)
        img.close()
        reduction = int(100 - (new_size / orig_size * 100))

        if dest_path is None and out_path != path:
            # in-place conversion from HEIC removed original file
            os.remove(path)
            path = out_path

        return out_path, new_size, reduction
