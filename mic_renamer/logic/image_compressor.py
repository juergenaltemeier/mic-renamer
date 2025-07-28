"""
This module provides the `ImageCompressor` class, a utility for compressing image files.
It supports reducing image file size by adjusting quality and/or resolution, and handles
HEIC conversion. The compression process is iterative to meet target file size or dimensions.
"""
from __future__ import annotations

import os
import logging
from pathlib import Path
import shutil
from PIL import Image
from PIL.Image import Resampling
from pillow_heif import register_heif_opener

# Register the HEIF opener with Pillow to enable HEIC file support.
register_heif_opener()

logger = logging.getLogger(__name__)


class ImageCompressor:
    """
    A utility class for compressing images to a target file size or dimensions.

    It supports iterative compression by reducing quality and/or resolution.
    """

    def __init__(
        self,
        max_size_kb: int = 2048,
        quality: int = 95,
        reduce_resolution: bool = True,
        resize_only: bool = False,
        max_width: int | None = None,
        max_height: int | None = None,
    ) -> None:
        """
        Initializes the ImageCompressor with compression parameters.

        Args:
            max_size_kb (int): Target maximum file size in kilobytes. Defaults to 2048 KB.
            quality (int): Initial JPEG quality (0-100). Defaults to 95.
            reduce_resolution (bool): If True, resolution will be reduced if quality reduction
                               alone is not sufficient to reach the target size. Defaults to True.
            resize_only (bool): If True, only resizing will be performed, no recompression
                                based on quality. Defaults to False.
            max_width (int | None): Maximum width for the image in pixels. If 0 or None,
                                    no width limit is applied. Defaults to None.
            max_height (int | None): Maximum height for the image in pixels. If 0 or None,
                                     no height limit is applied. Defaults to None.
        """
        self.max_size = max_size_kb * 1024  # Convert KB to bytes
        self.quality = quality
        self.reduce_resolution = reduce_resolution
        self.resize_only = resize_only
        self.max_width = max_width
        self.max_height = max_height

    def _handle_heic_conversion(self, img: Image.Image, path: str, out_path: str) -> tuple[Image.Image, str, str]:
        """
        Handles HEIC image conversion to JPEG if required.

        Args:
            img (Image.Image): The PIL Image object.
            path (str): The original path of the image.
            out_path (str): The current output path candidate.

        Returns:
            tuple[Image.Image, str, str]: A tuple containing the potentially converted Image object,
                                          the new format string (e.g., "JPEG"), and the updated output path.
        """
        if path.lower().endswith(".heic"):
            logger.info(f"Converting HEIC image {path} to JPEG for compression.")
            # Convert HEIC to RGB mode, as JPEG does not support alpha channels.
            img = img.convert("RGB")
            # Update the output path to have a .jpg extension.
            out_path = str(Path(out_path).with_suffix(".jpg"))
            return img, "JPEG", out_path
        return img, img.format, out_path

    def _resize_image(self, img: Image.Image) -> Image.Image:
        """
        Resizes the image based on configured maximum width and height.

        Args:
            img (Image.Image): The PIL Image object.

        Returns:
            Image.Image: The resized PIL Image object.
        """
        scale = 1.0
        # Calculate scaling factor based on max width.
        if self.max_width and img.width > self.max_width:
            scale = min(scale, self.max_width / img.width)
        # Calculate scaling factor based on max height.
        if self.max_height and img.height > self.max_height:
            scale = min(scale, self.max_height / img.height)
        
        # If scaling is needed, resize the image using LANCZOS resampling for high quality.
        if scale < 1.0:
            new_w = int(img.width * scale)
            new_h = int(img.height * scale)
            logger.info(f"Resizing image from {img.width}x{img.height} to {new_w}x{new_h}.")
            return img.resize((new_w, new_h), Resampling.LANCZOS)
        return img

    def _iterative_compress(self, img: Image.Image, out_path: str, fmt: str, exif_data: bytes | None) -> int:
        """
        Performs iterative compression by reducing quality and/or resolution until target size is met.

        Args:
            img (Image.Image): The PIL Image object.
            out_path (str): The path to save the compressed image.
            fmt (str): The format to save the image in.
            exif_data (bytes | None): EXIF data to preserve.

        Returns:
            int: The final size of the compressed image in bytes.
        """
        current_quality = self.quality
        save_kwargs: dict[str, bool | int | bytes] = {"optimize": True}
        if fmt == "JPEG":
            if not self.resize_only:
                save_kwargs["quality"] = current_quality
        if exif_data and fmt == "JPEG": # Only add exif data if format is JPEG
            save_kwargs["exif"] = exif_data

        # Initial save to get the current size.
        try:
            img.save(out_path, format=fmt, **save_kwargs)
            new_size = os.path.getsize(out_path)
        except (IOError, OSError) as e:
            logger.error(f"Error during initial image save for {out_path}: {e}")
            return 0 # Indicate failure

        # Iteratively reduce quality if the image is still too large and not in resize_only mode.
        if fmt == "JPEG" and not self.resize_only and new_size > self.max_size:
            while new_size > self.max_size and current_quality > 10:
                current_quality -= 5 # Reduce quality by 5
                save_kwargs["quality"] = current_quality
                try:
                    # Re-open the image from the output path to ensure we're working with the latest saved version
                    # and to release previous in-memory image data.
                    current_img = Image.open(out_path)
                    current_img.save(out_path, format=fmt, **save_kwargs)
                    new_size = os.path.getsize(out_path)
                    current_img.close() # Close the image after saving
                    logger.debug(f"Reduced quality to {current_quality}, new size: {new_size} bytes.")
                except (IOError, OSError) as e:
                    logger.error(f"Error during quality reduction save for {out_path}: {e}")
                    break # Exit loop on error

        # If still too large and resolution reduction is enabled, iteratively reduce resolution.
        if self.reduce_resolution and new_size > self.max_size:
            while new_size > self.max_size and img.width > 100 and img.height > 100:
                # Re-open the image from the output path for resolution reduction.
                current_img = Image.open(out_path)
                # Reduce dimensions by 10% each iteration.
                current_img = current_img.resize((int(current_img.width * 0.9), int(current_img.height * 0.9)), Resampling.LANCZOS)
                try:
                    current_img.save(out_path, format=fmt, **save_kwargs)
                    new_size = os.path.getsize(out_path)
                    current_img.close() # Close the image after saving
                    logger.debug(f"Reduced resolution to {current_img.width}x{current_img.height}, new size: {new_size} bytes.")
                except (IOError, OSError) as e:
                    logger.error(f"Error during resolution reduction save for {out_path}: {e}")
                    break # Exit loop on error
        return new_size

    def compress(
        self,
        path: str,
        convert_heic: bool = False,
        dest_path: str | None = None,
    ) -> tuple[str, int, int]:
        """
        Compresses an image file to meet the configured maximum size or dimensions.

        Args:
            path (str): The absolute path to the image file to compress.
            convert_heic (bool): If True, HEIC images will be converted to JPEG
                                    before compression. Defaults to False.
            dest_path (str | None): Optional absolute path to save the compressed image.
                                   If None, the original file will be overwritten.

        Returns:
            tuple[str, int, int]: A tuple containing:
            - The path to the compressed image (str).
            - The new size of the compressed image in bytes (int).
            - The percentage reduction in size (int).
            Returns (original_path, 0, 0) if the input path is not a file or an error occurs.
        """
        # Validate input path: ensure it exists and is a file.
        if not os.path.isfile(path):
            logger.warning(f"Input path is not a file or does not exist: {path}")
            return path, 0, 0

        out_path = dest_path or path
        orig_size = 0
        try:
            orig_size = os.path.getsize(path)
        except OSError as e:
            logger.error(f"Could not get size of file {path}: {e}")
            return path, 0, 0

        # Handle simple copy when no compression/conversion is required.
        # If original size is already within limits AND no HEIC conversion is needed,
        # just copy the file if a destination path is specified.
        if orig_size <= self.max_size and not (convert_heic and path.lower().endswith(".heic")):
            if dest_path:
                try:
                    shutil.copy2(path, out_path)
                    logger.info(f"Copied {path} to {out_path} as no compression/conversion needed.")
                except OSError as e:
                    logger.error(f"Failed to copy file {path} to {out_path}: {e}")
                    return path, 0, 0
            return out_path, orig_size, 0

        img: Image.Image | None = None
        try:
            # Open the image file.
            img = Image.open(path).copy()
            exif_data = img.info.get("exif")
            fmt = img.format

            # Handle HEIC conversion if enabled.
            if convert_heic:
                img, fmt, out_path = self._handle_heic_conversion(img, path, out_path)
                if path.lower().endswith(".heic"):
                    exif_data = None # Discard EXIF data if converting from HEIC to JPEG

            # Resize according to configured max dimensions.
            img = self._resize_image(img)

            # Perform iterative compression (quality and/or resolution reduction).
            new_size = self._iterative_compress(img, out_path, fmt, exif_data)

        except (IOError, OSError, Image.UnidentifiedImageError) as e:
            logger.error(f"Error processing image {path}: {e}")
            # Ensure any partially created output file is removed on error.
            if out_path != path and Path(out_path).exists():
                try:
                    Path(out_path).unlink()
                    logger.info(f"Cleaned up partial output file: {out_path}")
                except OSError as unlink_e:
                    logger.error(f"Failed to remove partial output file {out_path}: {unlink_e}")
            return path, 0, 0
        finally:
            # Ensure the image object is closed to release resources.
            if img:
                img.close()

        # Calculate size reduction percentage.
        reduction = int(100 - (new_size / orig_size * 100)) if orig_size > 0 else 0

        # If original file was HEIC and it was converted in-place (dest_path is None),
        # the original HEIC file needs to be removed as it was replaced by the JPEG.
        if dest_path is None and path.lower().endswith(".heic") and out_path != path:
            try:
                os.remove(path)
                logger.info(f"Removed original HEIC file {path} after in-place conversion.")
            except OSError as e:
                logger.error(f"Failed to remove original HEIC file {path}: {e}")

        return out_path, new_size, reduction
