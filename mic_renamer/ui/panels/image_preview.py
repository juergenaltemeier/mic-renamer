"""Widgets for image preview and zooming."""
from PySide6.QtWidgets import QWidget, QGraphicsView, QGraphicsScene
from PySide6.QtGui import QPixmap, QPainter, QImage, QImageReader
from PySide6.QtCore import Qt
import logging


class ImageViewer(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._log = logging.getLogger(__name__)
        scene = QGraphicsScene(self)
        self.setScene(scene)
        self.pixmap_item = None
        self.current_pixmap = None
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        # Center anchored transforms avoid distorted appearance on resize
        self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self._zoom_pct = 100
        self._rotation = 0
        self.setFocusPolicy(Qt.StrongFocus)
        self.placeholder_pixmap = self._create_placeholder_pixmap()

    def _create_placeholder_pixmap(self) -> QPixmap:
        """Return a simple cross-hatch placeholder pixmap."""
        size = 200
        pix = QPixmap(size, size)
        pix.fill(Qt.lightGray)
        painter = QPainter(pix)
        painter.setPen(Qt.darkGray)
        painter.drawLine(0, 0, size, size)
        painter.drawLine(0, size, size, 0)
        painter.end()
        return pix

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.apply_transformations()

    def load_image(self, path: str):
        if not path:
            self.set_pixmap(self.placeholder_pixmap)
            return
        reader = QImageReader(path)
        reader.setAutoTransform(True)
        img = reader.read()
        if img.isNull() and path.lower().endswith(".heic"):
            try:
                from PIL import Image
                from pillow_heif import register_heif_opener

                register_heif_opener()
                pil_img = Image.open(path)
                pil_img = pil_img.convert("RGBA")
                data = pil_img.tobytes("raw", "RGBA")
                img = QImage(data, pil_img.width, pil_img.height, QImage.Format_RGBA8888)
            except Exception:
                img = QImage()
        if img.isNull():
            self._log.warning("Failed to load image: %s", path)
            self.set_pixmap(self.placeholder_pixmap)
            return
        pix = QPixmap.fromImage(img)
        self.set_pixmap(pix)

    def set_pixmap(self, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            self.scene().clear()
            self.pixmap_item = None
            self.current_pixmap = None
            self._zoom_pct = 100
            self._rotation = 0
            self.reset_transform()
            return
        self.current_pixmap = pixmap
        self.scene().clear()
        self.pixmap_item = self.scene().addPixmap(pixmap)
        self.pixmap_item.setTransformationMode(Qt.SmoothTransformation)
        self.scene().setSceneRect(self.current_pixmap.rect())
        self._rotation = 0
        self._zoom_pct = 100 # Reset zoom when new image is loaded
        self.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        self._update_zoom_pct() # Update zoom percentage after fitInView

    def reset_transform(self):
        self.resetTransform()
        try:
            self.horizontalScrollBar().setValue(0)
            self.verticalScrollBar().setValue(0)
        except Exception:
            pass

    def _update_zoom_pct(self):
        """Update self._zoom_pct based on the current transformation."""
        if not self.pixmap_item:
            return

        scene_rect = self.scene().sceneRect()
        if scene_rect.isEmpty() or scene_rect.width() == 0 or scene_rect.height() == 0:
            return
        view_rect = self.viewport().rect()
        if view_rect.isEmpty():
            return

        x_scale = view_rect.width() / scene_rect.width()
        y_scale = view_rect.height() / scene_rect.height()
        base_factor = min(x_scale, y_scale)

        if base_factor == 0:
            return

        t = self.transform()
        current_scale = (t.m11() ** 2 + t.m21() ** 2) ** 0.5
        self._zoom_pct = (current_scale / base_factor) * 100

    def wheelEvent(self, event):
        if not self.pixmap_item:
            return

        factor = 1.15
        if event.angleDelta().y() < 0:
            factor = 1.0 / factor

        t = self.transform()
        current_scale = (t.m11() ** 2 + t.m21() ** 2) ** 0.5

        # Simple zoom limits to prevent extreme zoom
        if (current_scale > 10.0 and factor > 1.0) or (current_scale < 0.1 and factor < 1.0):
            return

        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.scale(factor, factor)
        self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)

        self._update_zoom_pct()
        event.accept()

    def apply_transformations(self):
        if not self.pixmap_item:
            return
        # Reset transformations before applying new ones
        self.resetTransform()
        # Apply rotation
        if self._rotation != 0:
            self.rotate(self._rotation)
        # Apply zoom percentage
        zoom_factor = self._zoom_pct / 100.0
        self.scale(zoom_factor, zoom_factor)

    def zoom_fit(self):
        if not self.pixmap_item:
            return
        self._zoom_pct = 100
        self.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        self._update_zoom_pct() # Update zoom percentage after fitInView
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
    def __init__(self, aspect_ratio: float | None = 16 / 9, parent=None):
        super().__init__(parent)
        self.aspect_ratio = aspect_ratio
        self._widget = None

    def setWidget(self, widget):
        self._widget = widget
        widget.setParent(self)

    def resizeEvent(self, event):
        if not self._widget:
            return super().resizeEvent(event)
        if self.aspect_ratio is None:
            super().resizeEvent(event)
            return
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
