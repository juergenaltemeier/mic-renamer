"""
This module provides utility functions for extracting metadata from media files,
primarily focusing on retrieving the capture date from image EXIF data.
It includes robust error handling and fallback mechanisms to ensure a date is
always returned.
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from PIL import Image, ExifTags

logger = logging.getLogger(__name__)


def get_capture_date(path: str | Path, date_format: str = "%y%m%d") -> str:
    """
    Extracts the capture date of an image file from its EXIF metadata.

    This function attempts to read the 'DateTimeOriginal' or 'DateTime' tags from the
    image's EXIF data. If EXIF data is not available, or if the date cannot be parsed
    from EXIF, it falls back to the file's last modification time. As a final fallback,
    if neither EXIF nor modification time can be retrieved, it returns the current date.

    Args:
        path (str | Path): The path to the image file.
        date_format (str): The desired format for the output date string.
                           Defaults to "%y%m%d" (e.g., 240728 for July 28, 2024).

    Returns:
        str: The capture date as a formatted string. Returns the current date as a string
             if no other date can be determined.
    """
    file_path = Path(path)

    # 1. Try to get the capture date from EXIF data
    try:
        # Open the image file using Pillow.
        with Image.open(file_path) as img:
            # Attempt to retrieve EXIF data. _getexif() returns a dictionary or None.
            exif_data = img.getexif()
            if exif_data:
                # Map EXIF tag IDs to their human-readable names.
                exif = {
                    ExifTags.TAGS[k]: v
                    for k, v in exif_data.items()
                    if k in ExifTags.TAGS
                }
            img.close() # Close image immediately after EXIF extraction
            # Prioritize 'DateTimeOriginal', then 'DateTime'.
            date_str = exif.get("DateTimeOriginal") or exif.get("DateTime")
            if date_str:
                try:
                    # Parse the EXIF date string (format: YYYY:MM:DD HH:MM:S S).
                    dt_obj = datetime.strptime(str(date_str), "%Y:%m:%d %H:%M:%S")
                    formatted_date = dt_obj.strftime(date_format)
                    logger.debug(f"Extracted EXIF date '{formatted_date}' for {file_path}")
                    return formatted_date
                except (ValueError, TypeError) as e:
                    # Log parsing errors but continue to fallbacks.
                    logger.warning(f"Could not parse EXIF date '{date_str}' from {file_path}: {e}")
            else:
                logger.debug(f"No EXIF data found for {file_path}")
    except (FileNotFoundError, Image.UnidentifiedImageError) as e:
        # Log if the file is not an image or cannot be opened.
        logger.warning(f"Could not open or identify image file {file_path} for EXIF: {e}")
    except Exception as e:
        # Catch any other unexpected errors during EXIF reading.
        logger.warning(f"An unexpected error occurred while reading EXIF from {file_path}: {e}")

    # 2. Fallback to file modification time
    try:
        # Get the last modification time of the file.
        ts = file_path.stat().st_mtime
        formatted_date = datetime.fromtimestamp(ts).strftime(date_format)
        logger.debug(f"Using modification time '{formatted_date}' for {file_path}")
        return formatted_date
    except FileNotFoundError:
        logger.warning(f"File not found for modification time check: {file_path}")
    except OSError as e:
        # Log OS errors (e.g., permission issues) during stat call.
        logger.warning(f"OS error getting modification time for {file_path}: {e}")
    except Exception as e:
        logger.warning(f"An unexpected error occurred while getting modification time for {file_path}: {e}")

    # 3. Final fallback to the current date
    current_date_str = datetime.now().strftime(date_format)
    logger.info(f"Falling back to current date '{current_date_str}' for {file_path}")
    return current_date_str

