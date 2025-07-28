"""
This module provides widgets for displaying various media types (images and videos)
within the application. It includes a `VideoPlayer` for video playback with controls
and a `MediaViewer` that intelligently switches between an image viewer and a video player
based on the file type.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Set

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget,
    QStackedLayout,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QSlider,
    QLabel,
    QMessageBox, # Added QMessageBox import
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

from .image_preview import ImageViewer
from ..constants import DEFAULT_MARGIN
from mic_renamer.utils.media_utils import get_video_codec, get_video_thumbnail

logger = logging.getLogger(__name__)


class VideoPlayer(QWidget):
    """
    A simple video player widget with basic playback controls (play/pause, seek).

    It uses `QMediaPlayer` and `QVideoWidget` for multimedia playback and provides
    error handling for unsupported formats or missing codecs.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initializes the VideoPlayer.

        Args:
            parent (QWidget | None): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self._log = logging.getLogger(__name__)
        
        # Initialize QMediaPlayer and QAudioOutput.
        self.player = QMediaPlayer(self) # The core media player.
        self.audio = QAudioOutput(self) # Audio output for the player.
        self.player.setAudioOutput(self.audio)
        
        # Initialize QVideoWidget to display video frames.
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: #f4f4f5;") # Set background color.
        self.player.setVideoOutput(self.video_widget) # Connect player to video output.

        # Label to display error messages if video playback fails.
        self.error_label = QLabel(
            "Cannot play video. The format may not be supported or required codecs are missing."
        )
        self.error_label.setWordWrap(True) # Enable word wrapping.
        self.error_label.setAlignment(Qt.AlignCenter) # Center align text.
        self.error_label.setStyleSheet("background-color: #f4f4f5;") # Set background color.

        # QStackedLayout to switch between video widget and error label.
        self.video_stack = QStackedLayout()
        self.video_stack.addWidget(self.video_widget)
        self.video_stack.addWidget(self.error_label)

        # Play/Pause button.
        self.btn_play = QPushButton("▶")
        self.btn_play.setCheckable(True) # Make it a toggle button.
        self.btn_play.toggled.connect(self.toggle_playback) # Connect to toggle playback method.

        # Position slider for seeking within the video.
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 0) # Initial range (0-0) until duration is known.
        self.position_slider.sliderMoved.connect(self.player.setPosition) # Connect to player's setPosition.

        # Connect QMediaPlayer signals to player control slots.
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._sync_button)
        self.player.errorOccurred.connect(self._on_error)

        # Main layout for the VideoPlayer widget.
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            DEFAULT_MARGIN, DEFAULT_MARGIN, DEFAULT_MARGIN, DEFAULT_MARGIN
        )
        layout.addLayout(self.video_stack) # Add the stacked layout for video/error display.
        
        # Horizontal layout for playback controls.
        controls = QHBoxLayout()
        controls.addWidget(self.btn_play)
        controls.addWidget(self.position_slider)
        layout.addLayout(controls) # Add controls to the main layout.
        logger.info("VideoPlayer UI setup complete.")

    def _on_error(self, error: QMediaPlayer.Error, error_string: str) -> None:
        """
        Slot to handle errors reported by QMediaPlayer.

        Displays a user-friendly error message and logs the detailed error.

        Args:
            error (QMediaPlayer.Error): The error code.
            error_string (str): A human-readable description of the error.
        """
        self._log.error(f"MediaPlayer Error: {error_string} (Code: {error.name})")
        # Construct an HTML-formatted error message for display.
        self.error_label.setText(
            '<html><body style="color: #333; background-color: #f4f4f5; padding: 10px;">'
            '<p><b>Cannot play video</b></p>'
            '<p>The format may not be supported or required codecs are missing.</p>'
            '<p>For the best experience, we recommend installing the K-Lite Codec Pack. It includes support for a wide range of video formats, including AV1.</p>'
            '<p><a href="https://codecguide.com/download_kl.htm" style="color: #0078d4;">Download K-Lite Codec Pack</a></p>'
            f'<p style="font-size: 9px; color: #666;">Details: {error_string}</p>'
            '</body></html>'
        )
        self.video_stack.setCurrentWidget(self.error_label) # Switch to display the error message.
        self.btn_play.setChecked(False) # Ensure play button is unchecked.
        self.player.stop() # Stop playback.
        logger.warning("Video playback error displayed to user.")

    def _check_services(self) -> bool:
        """
        Checks if multimedia services are available for video playback.

        If not available, it triggers the error display.

        Returns:
            bool: True if services are available, False otherwise.
        """
        if self.player.isAvailable():
            return True
        
        # If services are not available, display a generic error message.
        self._on_error(
            self.player.error(), # Pass the actual error code from the player.
            "Multimedia services are not available. Please install a codec pack."
        )
        logger.warning("Multimedia services not available.")
        return False

    def toggle_playback(self, playing: bool) -> None:
        """
        Toggles video playback (play/pause) based on the button's checked state.

        Args:
            playing (bool): True to play, False to pause.
        """
        if not self._check_services(): # Check if multimedia services are available.
            self.btn_play.setChecked(False) # Reset button state if services are down.
            return
        
        # If the error label is currently displayed, prevent playback.
        if self.video_stack.currentWidget() == self.error_label:
            self.btn_play.setChecked(False)
            logger.debug("Attempted to play video while error message is displayed. Aborting.")
            return
        
        if playing:
            self.player.play()
            logger.info("Video playback started.")
        else:
            self.player.pause()
            logger.info("Video playback paused.")

    def _sync_button(self) -> None:
        """
        Synchronizes the play/pause button's checked state with the player's playback state.
        """
        # Set button checked if player is in PlayingState, unchecked otherwise.
        self.btn_play.setChecked(self.player.playbackState() == QMediaPlayer.PlayingState)
        logger.debug(f"Play button synced. Is playing: {self.player.playbackState() == QMediaPlayer.PlayingState}")

    def _on_position_changed(self, pos: int) -> None:
        """
        Slot to update the position slider when the media player's position changes.

        Signals from the slider are temporarily blocked to prevent a feedback loop.

        Args:
            pos (int): The current playback position in milliseconds.
        """
        self.position_slider.blockSignals(True) # Block signals to prevent recursive calls.
        self.position_slider.setValue(pos) # Update slider position.
        self.position_slider.blockSignals(False) # Unblock signals.
        logger.debug(f"Slider position updated to {pos}ms.")

    def _on_duration_changed(self, dur: int) -> None:
        """
        Slot to update the position slider's range when the media player's duration changes.

        Args:
            dur (int): The total duration of the media in milliseconds.
        """
        self.position_slider.setRange(0, dur) # Set slider range from 0 to total duration.
        logger.debug(f"Slider duration range set to {dur}ms.")

    def load_video(self, path: str) -> None:
        """
        Loads a video file for playback.

        Args:
            path (str): The absolute path to the video file.
        """
        if not self._check_services(): # Ensure multimedia services are available.
            logger.warning("Cannot load video: multimedia services not available.")
            return
        
        self.video_stack.setCurrentWidget(self.video_widget) # Switch to display the video widget.
        url = QUrl.fromLocalFile(str(path)) # Convert local file path to QUrl.
        
        try:
            self.player.setSource(url) # Use setSource for newer PySide6 versions.
            logger.debug(f"Attempting to set video source using setSource: {path}")
        except AttributeError:
            # Fallback to setMedia for older PySide6 versions.
            self.player.setMedia(url)
            logger.debug(f"Attempting to set video source using setMedia (fallback): {path}")
        except Exception as e:
            self._log.error(f"Failed to set video source for {path}: {e}")
            self._on_error(QMediaPlayer.ResourceError, f"Failed to set video source: {e}")
            return

        self.player.pause() # Pause initially.
        self.position_slider.setValue(0) # Reset slider to start.
        self.btn_play.setChecked(False) # Ensure play button is unchecked.
        logger.info(f"Video loaded: {path}")


class MediaViewer(QWidget):
    """
    A composite widget that intelligently displays either an image or a video
    based on the file's extension.

    It uses an `ImageViewer` for images and a `VideoPlayer` for videos, switching
    between them using a `QStackedLayout`.
    """

    # Define sets of accepted image and video extensions.
    IMAGE_EXTS: Set[str] = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".heic"}
    VIDEO_EXTS: Set[str] = {".mp4", ".avi", ".mov", ".mkv"}

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initializes the MediaViewer.

        Args:
            parent (QWidget | None): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.image_viewer = ImageViewer() # Instance of the image viewer.
        self.video_player = VideoPlayer() # Instance of the video player.
        
        # QStackedLayout to manage switching between image and video viewers.
        self.stack = QStackedLayout(self)
        self.stack.addWidget(self.image_viewer)
        self.stack.addWidget(self.video_player)
        self.current_media_path: str | None = None # Initialize current_media_path
        logger.info("MediaViewer initialized.")

    def clear_media(self) -> None:
        """
        Clears any currently loaded media and stops video playback.

        Resets both the image viewer and video player to their initial empty states.
        """
        self.video_player.player.stop() # Stop video playback.
        self.video_player.player.setSource(QUrl()) # Clear the video media source.
        self.image_viewer.load_image("") # Clear the image viewer (loads placeholder).
        self.current_media_path = None # Reset current media path
        logger.info("MediaViewer cleared all loaded media.")

    def load_path(self, path: str) -> None:
        """
        Loads media (image or video) from the given file path.

        It determines the media type based on the file extension and delegates
        loading to the appropriate viewer/player. Special handling for AV1 video
        thumbnails is included.

        Args:
            path (str): The absolute path to the media file.
        """
        if not path:
            self.image_viewer.load_image("") # Load placeholder if path is empty.
            self.video_player.player.stop() # Stop any active video playback.
            self.stack.setCurrentWidget(self.image_viewer) # Ensure image viewer is shown.
            logger.debug("Empty path provided to MediaViewer. Clearing media.")
            return
        
        self.current_media_path = path # Update current media path
        ext = Path(path).suffix.lower() # Get file extension in lowercase.
        
        if ext in self.IMAGE_EXTS: # If it's an image file.
            self.image_viewer.load_image(path) # Load image.
            self.stack.setCurrentWidget(self.image_viewer) # Show image viewer.
            logger.info(f"Loaded image: {path}")
        elif ext in self.VIDEO_EXTS: # If it's a video file.
            codec = get_video_codec(path) # Attempt to get video codec.
            if codec == 'av1':
                logger.info(f"AV1 video detected: {path}. Attempting to load thumbnail.")
                pixmap = get_video_thumbnail(path) # Get thumbnail for AV1.
                if not pixmap.isNull():
                    self.show_pixmap(pixmap) # Display thumbnail if successful.
                    logger.info(f"Displayed AV1 thumbnail for {path}.")
                    return # Exit, as thumbnail is displayed.
                else:
                    logger.warning(f"Failed to get AV1 thumbnail for {path}. Attempting direct video load.")
            
            self.video_player.load_video(path) # Load video.
            self.stack.setCurrentWidget(self.video_player) # Show video player.
            logger.info(f"Loaded video: {path}")
        else: # Unsupported file type.
            self.image_viewer.load_image("") # Load placeholder.
            self.stack.setCurrentWidget(self.image_viewer) # Show image viewer.
            logger.warning(f"Unsupported media file type: {path}. Displaying placeholder.")

    def show_pixmap(self, pixmap: QPixmap) -> None:
        """
        Displays a preloaded QPixmap in the image viewer.

        This is useful for displaying thumbnails or other generated pixmaps directly.

        Args:
            pixmap (QPixmap): The QPixmap object to display.
        """
        self.image_viewer.set_pixmap(pixmap) # Set pixmap in the image viewer.
        self.stack.setCurrentWidget(self.image_viewer) # Ensure image viewer is active.
        logger.debug("Displayed preloaded pixmap.")

    # Expose image viewer controls as properties/methods of MediaViewer.
    @property
    def zoom_pct(self) -> int:
        """
        Returns the current zoom percentage of the image viewer.
        """
        return self.image_viewer._zoom_pct

    @zoom_pct.setter
    def zoom_pct(self, value: int) -> None:
        """
        Sets the zoom percentage of the image viewer.
        """
        self.image_viewer._zoom_pct = value

    def zoom_fit(self) -> None:
        """
        Calls the `zoom_fit` method on the active image viewer.
        """
        if self.stack.currentWidget() == self.image_viewer:
            self.image_viewer.zoom_fit()
            logger.debug("Zoom fit requested for image viewer.")
        else:
            logger.debug("Zoom fit ignored: video player is active.")

    def apply_transformations(self) -> None:
        """
        Calls the `apply_transformations` method on the active image viewer.
        """
        if self.stack.currentWidget() == self.image_viewer:
            self.image_viewer.apply_transformations()
            logger.debug("Apply transformations requested for image viewer.")
        else:
            logger.debug("Apply transformations ignored: video player is active.")

    def rotate_left(self) -> None:
        """
        Calls the `rotate_left` method on the active image viewer.
        """
        if self.stack.currentWidget() == self.image_viewer:
            self.image_viewer.rotate_left()
            logger.debug("Rotate left requested for image viewer.")
        else:
            logger.debug("Rotate left ignored: video player is active.")

    def rotate_right(self) -> None:
        """
        Calls the `rotate_right` method on the active image viewer.
        """
        if self.stack.currentWidget() == self.image_viewer:
            self.image_viewer.rotate_right()
            logger.debug("Rotate right requested for image viewer.")