from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider, QGraphicsView, QGraphicsScene
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtCore import Qt



class ImageViewer(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        scene = QGraphicsScene(self)
        self.setScene(scene)
        self.pixmap_item = None
        self.current_pixmap = None
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self._zoom_pct = 100
        self._rotation = 0
        self.setFocusPolicy(Qt.StrongFocus)

    def load_image(self, path: str):
        if not path:
            self.scene().clear()
            self.pixmap_item = None
            self.current_pixmap = None
            self._zoom_pct = 100
            self._rotation = 0
            self.reset_transform()
            return
        pix = QPixmap(path)
        if pix.isNull():
            self.scene().clear()
            self.pixmap_item = None
            self.current_pixmap = None
            self._zoom_pct = 100
            self._rotation = 0
            self.reset_transform()
            return
        self.current_pixmap = pix
        self.scene().clear()
        self.pixmap_item = self.scene().addPixmap(pix)
        self.scene().setSceneRect(self.pixmap_item.boundingRect())
        self._rotation = 0
        self.zoom_fit()

    def reset_transform(self):
        self.resetTransform()
        try:
            self.horizontalScrollBar().setValue(0)
            self.verticalScrollBar().setValue(0)
        except Exception:
            pass

    def wheelEvent(self, event):
        if not self.pixmap_item:
            return
        delta = event.angleDelta().y()
        if delta > 0:
            self._zoom_pct = min(self._zoom_pct + 10, 500)
        else:
            self._zoom_pct = max(self._zoom_pct - 10, 10)
        self.apply_transformations()
        event.accept()

    def apply_transformations(self):
        if not self.pixmap_item:
            return
        self.resetTransform()
        if self._rotation != 0:
            self.rotate(self._rotation)
        factor = self._zoom_pct / 100.0
        self.scale(factor, factor)
        try:
            self.horizontalScrollBar().setValue(0)
            self.verticalScrollBar().setValue(0)
        except Exception:
            pass

    def zoom_fit(self):
        if not self.pixmap_item:
            return
        view_rect = self.viewport().rect()
        scene_rect = self.scene().sceneRect().toRect()
        if scene_rect.isEmpty():
            return
        factor_w = view_rect.width() / scene_rect.width()
        factor_h = view_rect.height() / scene_rect.height()
        factor = min(factor_w, factor_h)
        self._zoom_pct = int(factor * 100)
        self.resetTransform()
        if self._rotation != 0:
            self.rotate(self._rotation)
        self.scale(factor, factor)
        try:
            self.horizontalScrollBar().setValue(0)
            self.verticalScrollBar().setValue(0)
        except Exception:
            pass

    def rotate_left(self):
        if not self.pixmap_item:
            return
        self._rotation = (self._rotation - 90) % 360
        self.apply_transformations()

    def rotate_right(self):
        if not self.pixmap_item:
            return
        self._rotation = (self._rotation + 90) % 360
        self.apply_transformations()


class AspectRatioWidget(QWidget):
    def __init__(self, aspect_ratio=16 / 9, parent=None):
        super().__init__(parent)
        self.aspect_ratio = aspect_ratio
        self._widget = None

    def setWidget(self, widget):
        self._widget = widget
        widget.setParent(self)

    def resizeEvent(self, event):
        if not self._widget:
            return super().resizeEvent(event)
        w = self.width()
        h = self.height()
        target_w = w
        target_h = int(target_w / self.aspect_ratio)
        if target_h > h:
            target_h = h
            target_w = int(target_h * self.aspect_ratio)
        x = (w - target_w) // 2
        y = (h - target_h) // 2
        self._widget.setGeometry(x, y, target_w, target_h)
        super().resizeEvent(event)


class ImagePreviewPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        btn_fit = QPushButton("Fit")
        btn_rot_left = QPushButton("⟲")
        btn_rot_right = QPushButton("⟳")
        toolbar.addWidget(btn_fit)
        toolbar.addWidget(btn_rot_left)
        toolbar.addWidget(btn_rot_right)
        layout.addLayout(toolbar)
        self.viewer = ImageViewer()
        ar = AspectRatioWidget()
        ar.setWidget(self.viewer)
        layout.addWidget(ar, 5)
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(10)
        self.zoom_slider.setMaximum(500)
        self.zoom_slider.setValue(100)
        layout.addWidget(self.zoom_slider)

        btn_fit.clicked.connect(self.viewer.zoom_fit)
        btn_rot_left.clicked.connect(self.viewer.rotate_left)
        btn_rot_right.clicked.connect(self.viewer.rotate_right)
        self.zoom_slider.valueChanged.connect(self.on_zoom)

    def on_zoom(self, value: int):
        self.viewer._zoom_pct = value
        self.viewer.apply_transformations()

    def load_image(self, path: str):
        self.viewer.load_image(path)
        self.zoom_slider.setValue(self.viewer._zoom_pct)


