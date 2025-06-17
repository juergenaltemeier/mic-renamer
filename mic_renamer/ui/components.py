# ui/components.py

from PySide6.QtWidgets import QListWidget, QListWidgetItem, QCheckBox
from PySide6.QtCore import Qt
import os

from ..logic.settings import ItemSettings

class DragDropListWidget(QListWidget):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setMinimumWidth(300)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            added = False
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if os.path.isfile(path):
                    ext = os.path.splitext(path)[1].lower()
                    if ext in ItemSettings.ACCEPT_EXTENSIONS:
                        exists = any(self.item(i).data(Qt.UserRole) == path for i in range(self.count()))
                        if not exists:
                            item = QListWidgetItem(os.path.basename(path))
                            item.setData(Qt.UserRole, path)
                            # Einstellungen später im main_window speichern
                            item.setData(Qt.UserRole + 1, None)
                            self.addItem(item)
                            added = True
            if added and self.currentItem() is None and self.count() > 0:
                self.setCurrentRow(0)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


class EnterToggleCheckBox(QCheckBox):
    """QCheckBox that toggles when Return or Enter is pressed."""

    def keyPressEvent(self, event) -> None:  # noqa: D401
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.toggle()
            event.accept()
        else:
            super().keyPressEvent(event)
