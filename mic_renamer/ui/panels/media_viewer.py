from __future__ import annotations

"""Combined image and video preview widgets."""

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import (
    QWidget,
    QStackedLayout,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QSlider,
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

from .image_preview import ImageViewer


class VideoPlayer(QWidget):
    """Simple video player with play/pause and seek controls."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.video_widget = QVideoWidget()
        self.player.setVideoOutput(self.video_widget)

        self.btn_play = QPushButton("▶")
        self.btn_play.setCheckable(True)
        self.btn_play.toggled.connect(self.toggle_playback)

        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.sliderMoved.connect(self.player.setPosition)

        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._sync_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.video_widget)
        controls = QHBoxLayout()
        controls.addWidget(self.btn_play)
        controls.addWidget(self.position_slider)
        layout.addLayout(controls)

    def toggle_playback(self, playing: bool) -> None:
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
            self.video_player.load_video(path)
            self.stack.setCurrentWidget(self.video_player)
        else:
            self.image_viewer.load_image("")
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

