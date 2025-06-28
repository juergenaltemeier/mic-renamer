# ui/components.py

from PySide6.QtWidgets import QListWidget, QListWidgetItem, QCheckBox, QWidget, QVBoxLayout, QLabel
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


class TagBox(QWidget):
    """A custom widget that displays a tag with a checkbox in a styled box."""

    toggled = Signal(bool)

    def __init__(self, code: str, description: str, parent=None):
        super().__init__(parent)
        self.code = code
        self.description = description
        self.is_checked = False
        self._preselected = False

        self.setContentsMargins(0, 0, 0, 0)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)

        self.checkbox = EnterToggleCheckBox(f"{code}: {description}")
        self.checkbox.toggled.connect(self._update_style)
        self.checkbox.toggled.connect(self.toggled)

        layout.addWidget(self.checkbox)

        self._update_style(self.is_checked)
        self.setToolTip(f"{self.code}: {self.description}")

    def set_preselected(self, preselected: bool):
        if self._preselected != preselected:
            self._preselected = preselected
            self._update_style(self.is_checked)

    def _update_style(self, checked):
        self.is_checked = checked
        if self._preselected:
            self.setProperty("class", "tag-box-preselected")
        elif checked:
            self.setProperty("class", "tag-box-checked")
        else:
            self.setProperty("class", "tag-box")

        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event):
        self.checkbox.toggle()
        event.accept()

    def setChecked(self, checked):
        self.checkbox.setChecked(checked)

    def isChecked(self):
        return self.checkbox.isChecked()

    def toggle(self):
        self.checkbox.toggle()
