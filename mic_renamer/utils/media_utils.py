import subprocess
import tempfile
import os
import sys
import logging
from pathlib import Path
from PySide6.QtGui import QPixmap

__all__ = ["get_video_codec", "get_video_thumbnail"]

def get_ffmpeg_path() -> str:
    """
    Return a usable ffmpeg executable path.
    First tries to use imageio-ffmpeg's bundled binary, then bundled resources,
    then falls back to system 'ffmpeg' on PATH.
    """
    logger = logging.getLogger(__name__)
    # try imageio-ffmpeg bundled executable
    try:
        from imageio_ffmpeg import get_ffmpeg_exe
        exe = get_ffmpeg_exe()
        logger.debug("Using imageio_ffmpeg binary: %s", exe)
        return exe
    except ImportError:
        pass
    # try our bundled ffmpeg in resources
    base = Path(__file__).parent.parent / 'resources' / 'ffmpeg'
    if sys.platform.startswith('win'):
        p = base / 'windows' / 'ffmpeg.exe'
    elif sys.platform == 'darwin':
        p = base / 'macos' / 'ffmpeg'
    else:
        p = base / 'linux' / 'ffmpeg'
    if p.exists() and os.access(p, os.X_OK):
        logger.debug("Using bundled ffmpeg binary: %s", p)
        return str(p)
    # fallback to system ffmpeg
    logger.debug("Falling back to system ffmpeg on PATH")
    return 'ffmpeg'

def get_video_codec(path: str) -> str:
    ffmpeg = get_ffmpeg_path()
    # Probe stream info via ffmpeg stderr (hide banner to reduce noise)
    cmd = [ffmpeg, '-hide_banner', '-i', path]
    try:
        p = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL)
        _, err = p.communicate(timeout=5)
        info = err.decode(errors='ignore')
    except Exception:
        return ''
    # Look for the first video stream line: contains 'Video:'
    for line in info.splitlines():
        if 'Video:' in line:
            # e.g. '  Stream #0:0: Video: av1 (Main), ...'
            after = line.split('Video:')[1].strip()
            # codec name is first word
            codec = after.split()[0]
            return codec.lower()
    return ''

def get_video_thumbnail(path: str) -> QPixmap:
    ffmpeg = get_ffmpeg_path()
    fd, tmp = tempfile.mkstemp(suffix='.jpg')
    os.close(fd)
    cmd = [ffmpeg, '-y', '-loglevel', 'error', '-i', path, '-frames:v', '1', tmp]
    try:
        subprocess.run(cmd, check=True)
        pixmap = QPixmap(tmp)
    except Exception as e:
        logging.getLogger(__name__).error('ffmpeg thumbnail error: %s', e)
        pixmap = QPixmap()
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass
    return pixmap