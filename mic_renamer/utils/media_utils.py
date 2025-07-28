"""
This module provides utilities for interacting with media files, specifically for
extracting video codecs and generating video thumbnails using the FFmpeg tool.
It includes logic to locate the FFmpeg executable and handles various errors
that may occur during media processing.
"""
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PySide6.QtGui import QPixmap

# Define all public functions exposed by this module.
__all__ = ["get_video_codec", "get_video_thumbnail"]

logger = logging.getLogger(__name__)


def get_ffmpeg_path() -> str:
    """
    Locates and returns a usable path to the FFmpeg executable.

    The search order is prioritized as follows:
    1.  FFmpeg binary bundled with the `imageio-ffmpeg` library.
    2.  FFmpeg binary bundled directly within the application's `resources` folder
        (platform-specific).
    3.  System's FFmpeg executable, assuming it's available in the system's PATH.

    Returns:
        str: The absolute path to the FFmpeg executable. If no specific path is found,
             it returns 'ffmpeg', relying on the system's PATH environment variable.
    """
    logger.debug("Attempting to find ffmpeg executable...")

    # 1. Try imageio-ffmpeg bundled executable
    try:
        from imageio_ffmpeg import get_ffmpeg_exe

        exe = get_ffmpeg_exe()
        if Path(exe).is_file() and os.access(exe, os.X_OK):
            logger.info(f"Using imageio-ffmpeg bundled binary: {exe}")
            return exe
        else:
            logger.warning(f"Imageio-ffmpeg binary found at {exe} but is not a file or not executable. Trying next.")
    except ImportError:
        logger.debug("imageio-ffmpeg not installed or not found. Trying next.")
    except Exception as e:
        logger.warning(f"Error while trying imageio-ffmpeg: {e}. Trying next.")

    # 2. Try our bundled ffmpeg in resources
    # Construct the base path to the bundled ffmpeg executables.
    base_path = Path(__file__).parent.parent / "resources" / "ffmpeg"
    
    # Determine the platform-specific path for the ffmpeg executable.
    if sys.platform.startswith("win"):
        p = base_path / "windows" / "ffmpeg.exe"
    elif sys.platform == "darwin": # macOS
        p = base_path / "macos" / "ffmpeg"
    else: # Linux and other Unix-like systems
        p = base_path / "linux" / "ffmpeg"

    # Check if the bundled executable exists and is executable.
    if p.exists() and os.access(p, os.X_OK):
        logger.info(f"Using bundled ffmpeg binary: {p}")
        return str(p)
    else:
        logger.warning(f"Bundled ffmpeg binary not found or not executable at {p}. Trying system PATH.")

    # 3. Fallback to system ffmpeg (relying on it being in the system's PATH)
    logger.info("Falling back to system ffmpeg on PATH.")
    return "ffmpeg"


def get_video_codec(path: str | Path) -> str:
    """
    Retrieves the video codec of a given media file using FFmpeg.

    Args:
        path (str | Path): The absolute path to the video file.

    Returns:
        str: The video codec name in lowercase (e.g., "h264", "av1").
             Returns an empty string if the codec cannot be determined due to errors
             (e.g., file not found, FFmpeg not accessible, invalid video file).
    """
    # Ensure the path is a string for subprocess compatibility.
    file_path_str = str(path)
    ffmpeg_path = get_ffmpeg_path()
    
    # FFmpeg command to get stream information. -hide_banner suppresses FFmpeg's startup banner.
    # -i specifies the input file. Output is redirected to stderr for parsing codec info.
    cmd = [ffmpeg_path, "-hide_banner", "-i", file_path_str]

    try:
        # Execute the FFmpeg command as a subprocess.
        # stderr is captured to parse video stream information.
        # stdout is redirected to DEVNULL as it's not needed.
        # text=True decodes stdout/stderr as text.
        # errors="ignore" handles potential decoding errors in FFmpeg output.
        proc = subprocess.Popen(
            cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True, errors="ignore"
        )
        # Wait for the process to complete, with a timeout.
        _, err = proc.communicate(timeout=5)
        
        # Parse the stderr output to find the video codec.
        for line in err.splitlines():
            if "Video:" in line:
                try:
                    # Example line: '  Stream #0:0: Video: av1 (Main), ...'
                    # Split by "Video:" and take the second part, then strip whitespace.
                    after_video = line.split("Video:")[1].strip()
                    # The codec name is typically the first word after "Video:".
                    codec = after_video.split()[0]
                    logger.info(f"Successfully determined video codec for {path}: {codec.lower()}")
                    return codec.lower()
                except IndexError:
                    # Log if parsing fails for a specific line but continue searching.
                    logger.warning(f"Could not parse video codec from line: {line}")
                    continue
        logger.warning(f"No video stream information found for {path}.")
        return "" # No video stream found or codec could not be extracted.

    except (subprocess.TimeoutExpired) as e:
        logger.error(f"Timeout (5s) getting video codec for {path}: {e}")
        proc.kill() # Terminate the process if it timed out.
        proc.wait() # Wait for the process to actually terminate.
        return ""
    except FileNotFoundError:
        logger.error(f"FFmpeg executable not found when trying to get video codec for {path}. Check PATH or bundled files.")
        return ""
    except OSError as e:
        logger.error(f"OS error when running FFmpeg for {path} (codec detection): {e}")
        return ""
    except Exception as e:
        logger.error(f"An unexpected error occurred while getting video codec for {path}: {e}")
        return ""


def get_video_thumbnail(path: str | Path) -> QPixmap:
    """
    Extracts a thumbnail (as a QPixmap) from a video file using FFmpeg.

    Args:
        path (str | Path): The absolute path to the video file.

    Returns:
        QPixmap: A QPixmap object representing the video thumbnail. Returns an empty
                 QPixmap if the thumbnail extraction fails for any reason.
    """
    # Ensure the path is a string for subprocess compatibility.
    file_path_str = str(path)
    ffmpeg_path = get_ffmpeg_path()
    tmp_path: Path | None = None
    pixmap = QPixmap() # Initialize with an empty QPixmap

    try:
        # Create a temporary file to save the extracted thumbnail.
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
        
        # FFmpeg command to extract a single frame (thumbnail) from the video.
        # -y: Overwrite output files without asking.
        # -loglevel error: Only show errors.
        # -i: Input file.
        # -frames:v 1: Extract only 1 video frame.
        cmd = [ffmpeg_path, "-y", "-loglevel", "error", "-i", file_path_str, "-frames:v", "1", str(tmp_path)]

        logger.debug(f"Executing ffmpeg for thumbnail: {' '.join(cmd)}")
        # Execute the FFmpeg command. `check=True` raises CalledProcessError for non-zero exit codes.
        # `timeout` prevents hanging on problematic video files.
        subprocess.run(cmd, check=True, timeout=10)
        
        # If FFmpeg command is successful, load the generated image into a QPixmap.
        if tmp_path and tmp_path.is_file() and tmp_path.stat().st_size > 0:
            pixmap = QPixmap(str(tmp_path))
            if pixmap.isNull():
                logger.warning(f"QPixmap could not load image from temporary file: {tmp_path}")
            else:
                logger.info(f"Successfully extracted thumbnail for {path} to {tmp_path}")
        else:
            logger.warning(f"FFmpeg did not create a valid temporary thumbnail file for {path} at {tmp_path}.")

    except (subprocess.CalledProcessError) as e:
        logger.error(f"FFmpeg command failed for {path} (thumbnail): {e}. Stderr: {e.stderr}")
    except (subprocess.TimeoutExpired) as e:
        logger.error(f"Timeout (10s) extracting thumbnail for {path}: {e}")
        if e.stdout: logger.error(f"Stdout: {e.stdout.decode()}")
        if e.stderr: logger.error(f"Stderr: {e.stderr.decode()}")
    except FileNotFoundError:
        logger.error(f"FFmpeg executable not found when trying to get thumbnail for {path}. Check PATH or bundled files.")
    except OSError as e:
        logger.error(f"OS error when running FFmpeg for {path} (thumbnail extraction): {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while extracting thumbnail for {path}: {e}")
    finally:
        # Ensure the temporary file is deleted, even if errors occurred.
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
                logger.debug(f"Cleaned up temporary thumbnail file: {tmp_path}")
            except OSError as e:
                logger.error(f"Failed to remove temporary thumbnail file {tmp_path}: {e}")
    
    return pixmap
