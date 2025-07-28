"""
This module provides functionality for converting image files, specifically handling HEIC
conversion to JPEG or PNG, and general image conversion to JPEG. It leverages Pillow
and pillow_heif for image processing and includes robust error handling and logging.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image
from pillow_heif import register_heif_opener

from ..utils.i18n import tr

# Register the HEIF opener with Pillow to enable HEIC file support.
register_heif_opener()


def _convert_image(
    src_path: Path, dest_path: Path, new_format: str, remove_original: bool = True
) -> Path | None:
    """
    A helper function to convert an image from a source path to a destination path
    in a specified new format.

    Args:
        src_path (Path): The path to the source image file.
        dest_path (Path): The path where the converted image file will be saved.
        new_format (str): The target image format (e.g., "JPEG", "PNG").
        remove_original (bool): If True, the original source file will be deleted
                                after a successful conversion. Defaults to True.

    Returns:
        Path | None: The path to the converted image if successful, otherwise None.
    """
    logger = logging.getLogger(__name__)
    try:
        # Open the source image file.
        with Image.open(src_path) as img:
            # Attempt to retrieve EXIF data. _getexif() returns a dictionary or None.
            exif_data = img.info.get("exif")

            # Convert to RGB if the target format (JPEG) does not support alpha channels
            # and the image mode includes an alpha channel (RGBA) or is paletted (P).
            if new_format == "JPEG" and img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
                # Discard EXIF data if converting from RGBA/P to RGB for JPEG, as it might be incompatible.
                exif_data = None

            # Prepare keyword arguments for the save operation.
            save_kwargs = {"format": new_format}
            # If EXIF data exists, include it in the save arguments to preserve metadata.
            if exif_data:
                # Filter out problematic EXIF tags like MakerNote, which can cause issues.
                # This requires parsing the EXIF data first.
                try:
                    # Use getexif() to get a proper Exif object
                    decoded_exif = img.getexif()
                    if decoded_exif:
                        # Create a new dictionary for filtered tags
                        filtered_exif_dict = {}
                        for key, value in decoded_exif.items():
                            # Exclude MakerNote and other potentially problematic tags
                            if ExifTags.TAGS.get(key) != 'MakerNote':
                                filtered_exif_dict[key] = value
                        
                        # Convert the filtered dictionary back to bytes for saving
                        if filtered_exif_dict:
                            # Create a new Exif object from the filtered dictionary
                            new_exif_obj = Image.Exif()
                            for k, v in filtered_exif_dict.items():
                                new_exif_obj[k] = v
                            save_kwargs["exif"] = new_exif_obj.tobytes()
                except Exception as e:
                    logger.warning(f"Error processing EXIF data for {src_path}: {e}. Discarding EXIF.")
                    exif_data = None # Discard EXIF on error

            # Save the image to the destination path with the specified format and EXIF data.
            img.save(dest_path, **save_kwargs)
            logger.info(f"Successfully converted {src_path} to {dest_path}")

        # If conversion was successful and remove_original is True, attempt to delete the source file.
        if remove_original:
            try:
                src_path.unlink()
                logger.info(f"Removed original file: {src_path}")
            except OSError as e:
                # Log an error if the original file cannot be removed.
                logger.error(f"Failed to remove original file {src_path}: {e}")
        
        return dest_path

    except (IOError, OSError) as e:
        # Catch and log errors related to file I/O or operating system issues during conversion.
        logger.error(f"Failed to convert image {src_path} to {new_format}: {e}")
        # If conversion fails, ensure any partially created destination file is removed
        # to prevent corrupted or incomplete files.
        if dest_path.exists():
            try:
                dest_path.unlink()
            except OSError as unlink_e:
                # Log if the cleanup of the destination file also fails.
                logger.error(f"Failed to remove partially created file {dest_path} after conversion error: {unlink_e}")
        return None


def convert_to_jpeg(path: str | Path) -> str:
    """
    Converts an image to JPEG format, preserving EXIF data.

    If the image is already a JPEG (case-insensitive check on suffix), it returns the original path
    without performing any conversion. If conversion is successful, the original file is deleted.

    Args:
        path (str | Path): The path to the image file to be converted.

    Returns:
        str: The path to the converted JPEG image. If conversion is not needed (already JPEG)
             or if it fails, the original path is returned.
    """
    src_path = Path(path)
    # Check if the file is already a JPEG; if so, no conversion is needed.
    if src_path.suffix.lower() in {".jpg", ".jpeg"}:
        return str(src_path)

    # Define the destination path with a .jpg extension.
    dest_path = src_path.with_suffix(".jpg")
    
    # Attempt to convert the image to JPEG using the helper function.
    converted_path = _convert_image(src_path, dest_path, "JPEG")
    
    # Return the path to the converted file if successful, otherwise return the original path.
    return str(converted_path) if converted_path else str(src_path)


def convert_heic(path: str | Path) -> str:
    """
    Converts a HEIC image to either JPEG or PNG format, preserving EXIF data.

    The target format (JPEG or PNG) is chosen based on whether the HEIC image
    contains an alpha channel (transparency). If an alpha channel is present,
    it converts to PNG; otherwise, it converts to JPEG. If conversion is successful,
    the original HEIC file is deleted.

    Args:
        path (str | Path): The path to the HEIC image file to be converted.

    Returns:
        str: The path to the converted image. If the input is not a HEIC file
             or if conversion fails, the original path is returned.
    """
    src_path = Path(path)
    # Check if the file is a HEIC image; if not, return the original path.
    if src_path.suffix.lower() != ".heic":
        return str(src_path)

    logger = logging.getLogger(__name__)
    try:
        # Open the HEIC image to inspect its properties, specifically for an alpha channel.
        with Image.open(src_path) as img:
            # Determine if the image has an alpha channel (transparency).
            has_alpha = "A" in img.getbands()

        # Choose the output format based on the presence of an alpha channel.
        if has_alpha:
            dest_path = src_path.with_suffix(".png")
            new_format = "PNG"
        else:
            dest_path = src_path.with_suffix(".jpg")
            new_format = "JPEG"
            
        # Attempt to convert the HEIC image using the helper function.
        converted_path = _convert_image(src_path, dest_path, new_format)
        
        # Return the path to the converted file if successful, otherwise return the original path.
        return str(converted_path) if converted_path else str(src_path)

    except (IOError, OSError) as e:
        # Catch and log errors if the HEIC file cannot be opened or inspected.
        logger.error(f"Failed to open or inspect HEIC file {src_path}: {e}")
        # Return the original path if an error occurs during inspection.
        return str(src_path)