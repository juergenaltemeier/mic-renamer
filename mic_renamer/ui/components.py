# ui/components.py

from PySide6.QtWidgets import QListWidget, QListWidgetItem, QCheckBox, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal
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


class TagBox(EnterToggleCheckBox):
    """A custom checkbox that displays a tag as rich text."""
    def __init__(self, code: str, description: str, parent=None):
        super().__init__(parent)
        self.code = code
        self.description = description
        self._preselected = False

        # display code on first line and description on second line
        self.setText(f"{code.upper()}\n{description}")
        self.setToolTip(f"{code}: {description}")
        # style update on toggle
        self.toggled.connect(self._update_style)
        self._update_style(self.isChecked())

    def set_text(self, code: str, description: str):
        self.code = code
        self.description = description
        self.setText(f"{code.upper()}\n{description}")
        self.setToolTip(f"{code}: {description}")

    def set_preselected(self, preselected: bool):
        if self._preselected != preselected:
            self._preselected = preselected
            self._update_style(self.isChecked())

    def _update_style(self, checked: bool):
        if self._preselected:
            self.setProperty("class", "tag-box-preselected")
        elif checked:
            self.setProperty("class", "tag-box-checked")
        else:
            self.setProperty("class", "tag-box")
        self.style().unpolish(self)
        self.style().polish(self)
