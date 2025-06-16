"""Simple image compression utilities."""
from __future__ import annotations

import os
from pathlib import Path
from PIL import Image


class ImageCompressor:
    """Compress images using Pillow."""

    def __init__(self, max_size_mb: int = 2, quality: int = 95, reduce_resolution: bool = True):
        self.max_size = max_size_mb * 1024 * 1024
        self.quality = quality
        self.reduce_resolution = reduce_resolution

    def compress(self, path: str) -> tuple[int, int]:
        """Compress ``path`` in-place.

        Returns a tuple of ``(new_size, reduction_percent)``.
        """
        if not os.path.isfile(path):
            return 0, 0
        orig_size = os.path.getsize(path)
        if orig_size <= self.max_size:
            return orig_size, 0
        img = Image.open(path)
        fmt = img.format
        save_kwargs = {"optimize": True}
        if fmt == "JPEG":
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
        return new_size, reduction
