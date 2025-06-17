"""Simple image compression utilities."""
from __future__ import annotations

import os
from pathlib import Path
from PIL import Image
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

    def compress(self, path: str, convert_heic: bool = False) -> tuple[str, int, int]:
        """Compress ``path`` in-place.

        Returns a tuple ``(new_path, new_size, reduction_percent)``.
        ``new_path`` may differ if HEIC conversion occurs.
        """
        if not os.path.isfile(path):
            return path, 0, 0
        orig_size = os.path.getsize(path)
        if orig_size <= self.max_size and not (convert_heic and path.lower().endswith(".heic")):
            return path, orig_size, 0

        if convert_heic and path.lower().endswith(".heic"):
            dest_path = str(Path(path).with_suffix(".jpg"))
            img = Image.open(path)
            img = img.convert("RGB")
            img.save(dest_path, "JPEG", quality=self.quality)
            img.close()
            os.remove(path)
            path = dest_path
            orig_size = os.path.getsize(path)

        img = Image.open(path)
        fmt = img.format

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
                img = img.resize((new_w, new_h), Image.LANCZOS)

        save_kwargs = {"optimize": True}
        if fmt == "JPEG" and not self.resize_only:
            save_kwargs["quality"] = self.quality

        img.save(path, format=fmt, **save_kwargs)
        new_size = os.path.getsize(path)
        if self.reduce_resolution and new_size > self.max_size:
            while new_size > self.max_size and img.width > 100 and img.height > 100:
                img = img.resize((int(img.width * 0.9), int(img.height * 0.9)), Image.LANCZOS)
                img.save(path, format=fmt, **save_kwargs)
                new_size = os.path.getsize(path)
        img.close()
        reduction = int(100 - (new_size / orig_size * 100))
        return path, new_size, reduction
