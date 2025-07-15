from __future__ import annotations

import logging
from pathlib import Path

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
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

from .image_preview import ImageViewer
from ..constants import DEFAULT_MARGIN
from mic_renamer.utils.media_utils import get_video_codec, get_video_thumbnail

"""Combined image and video preview widgets."""


class VideoPlayer(QWidget):
    """Simple video player with play/pause and seek controls."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._log = logging.getLogger(__name__)
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: #f4f4f5;")
        self.player.setVideoOutput(self.video_widget)

        self.error_label = QLabel(
            "Cannot play video. The format may not be supported or required codecs are missing."
        )
        self.error_label.setWordWrap(True)
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet("background-color: #f4f4f5;")

        self.video_stack = QStackedLayout()
        self.video_stack.addWidget(self.video_widget)
        self.video_stack.addWidget(self.error_label)

        self.btn_play = QPushButton("▶")
        self.btn_play.setCheckable(True)
        self.btn_play.toggled.connect(self.toggle_playback)

        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.sliderMoved.connect(self.player.setPosition)

        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._sync_button)
        self.player.errorOccurred.connect(self._on_error)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            DEFAULT_MARGIN, DEFAULT_MARGIN, DEFAULT_MARGIN, DEFAULT_MARGIN
        )
        layout.addLayout(self.video_stack)
        controls = QHBoxLayout()
        controls.addWidget(self.btn_play)
        controls.addWidget(self.position_slider)
        layout.addLayout(controls)

    def _on_error(self, error, error_string):
        self._log.error("MediaPlayer Error: %s", error_string)
        self.error_label.setText(
            '<html><body style="color: #333; background-color: #f4f4f5; padding: 10px;">'
            '<p><b>Cannot play video</b></p>'
            '<p>The format may not be supported or required codecs are missing.</p>'
            '<p>For the best experience, we recommend installing the K-Lite Codec Pack. It includes support for a wide range of video formats, including AV1.</p>'
            '<p><a href="https://codecguide.com/download_kl.htm" style="color: #0078d4;">Download K-Lite Codec Pack</a></p>'
            f'<p style="font-size: 9px; color: #666;">Details: {error_string}</p>'
            '</body></html>'
        )
        self.video_stack.setCurrentWidget(self.error_label)

    def _check_services(self):
        if self.player.isAvailable():
            return True
        
        self._on_error(
            self.player.error(),
            "Multimedia services are not available. Please install a codec pack."
        )
        return False

    def toggle_playback(self, playing: bool) -> None:
        if not self._check_services():
            self.btn_play.setChecked(False)
            return
        if self.video_stack.currentWidget() == self.error_label:
            self.btn_play.setChecked(False)
            return
        if playing:
            self.player.play()
        else:
            self.player.pause()

    def _sync_button(self) -> None:
        self.btn_play.setChecked(self.player.playbackState() == QMediaPlayer.PlayingState)

    def _on_position_changed(self, pos: int) -> None:
        self.position_slider.blockSignals(True)
        self.position_slider.setValue(pos)
        self.position_slider.blockSignals(False)

    def _on_duration_changed(self, dur: int) -> None:
        self.position_slider.setRange(0, dur)

    def load_video(self, path: str) -> None:
        if not self._check_services():
            return
        self.video_stack.setCurrentWidget(self.video_widget)
        url = QUrl.fromLocalFile(str(path))
        try:
            self.player.setSource(url)  # newer PySide6
        except AttributeError:
            self.player.setMedia(url)  # fallback for older versions
        self.player.pause()
        self.position_slider.setValue(0)
        self.btn_play.setChecked(False)


class MediaViewer(QWidget):
    """Display either an image or a video depending on file type."""

    IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".heic"}
    VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv"}

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.image_viewer = ImageViewer()
        self.video_player = VideoPlayer()
        self.stack = QStackedLayout(self)
        self.stack.addWidget(self.image_viewer)
        self.stack.addWidget(self.video_player)

    def clear_media(self) -> None:
        """Clear any loaded media and stop playback."""
        self.video_player.player.stop()
        self.video_player.player.setSource(QUrl()) # Clear the media source
        self.image_viewer.load_image("") # Clear image viewer

    def load_path(self, path: str) -> None:
        if not path:
            self.image_viewer.load_image("")
            self.video_player.player.stop()
            self.stack.setCurrentWidget(self.image_viewer)
            return
        ext = Path(path).suffix.lower()
        if ext in self.IMAGE_EXTS:
            self.image_viewer.load_image(path)
            self.stack.setCurrentWidget(self.image_viewer)
        elif ext in self.VIDEO_EXTS:
            codec = get_video_codec(path)
            if codec == 'av1':
                pixmap = get_video_thumbnail(path)
                if not pixmap.isNull():
                    self.show_pixmap(pixmap)
                    return
            self.video_player.load_video(path)
            self.stack.setCurrentWidget(self.video_player)
        else:
            self.image_viewer.load_image("")
            self.stack.setCurrentWidget(self.image_viewer)

    def show_pixmap(self, pixmap: QPixmap) -> None:
        """Display a preloaded pixmap."""
        self.image_viewer.set_pixmap(pixmap)
        self.stack.setCurrentWidget(self.image_viewer)

    # expose image viewer controls
    @property
    def zoom_pct(self) -> int:
        return self.image_viewer._zoom_pct

    @zoom_pct.setter
    def zoom_pct(self, value: int) -> None:
        self.image_viewer._zoom_pct = value

    def zoom_fit(self) -> None:
        if self.stack.currentWidget() == self.image_viewer:
            self.image_viewer.zoom_fit()

    def apply_transformations(self) -> None:
        if self.stack.currentWidget() == self.image_viewer:
            self.image_viewer.apply_transformations()

    def rotate_left(self) -> None:
        if self.stack.currentWidget() == self.image_viewer:
            self.image_viewer.rotate_left()

    def rotate_right(self) -> None:
        if self.stack.currentWidget() == self.image_viewer:
            self.image_viewer.rotate_right()
