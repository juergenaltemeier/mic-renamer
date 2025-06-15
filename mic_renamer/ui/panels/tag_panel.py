"""Panel showing available tags as checkboxes."""
from PySide6.QtWidgets import QWidget, QGridLayout, QVBoxLayout, QLabel, QCheckBox
from PySide6.QtCore import Qt, Signal
import logging

from ...logic.tag_loader import load_tags
from ...utils.i18n import tr


class TagPanel(QWidget):
    """Panel showing available tags as checkboxes."""

    tagToggled = Signal(str, int)

    def __init__(self, parent=None, tags_info: dict | None = None):
        super().__init__(parent)
        self._log = logging.getLogger(__name__)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr("select_tags_label")))
        self.checkbox_container = QWidget()
        self.tag_layout = QGridLayout(self.checkbox_container)
        self.tag_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.checkbox_container)
        self.checkbox_map: dict[str, QCheckBox] = {}
        self.tags_info: dict[str, str] | None = tags_info
        self.rebuild()

    def rebuild(self):
        while self.tag_layout.count():
            item = self.tag_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.checkbox_map = {}
        tags = self.tags_info if self.tags_info is not None else load_tags()
        if not isinstance(tags, dict):
            self._log.warning("Invalid tags info, expected dict but got %s", type(tags).__name__)
            tags = {}
        self.tags_info = tags
        if not self.tags_info:
            self.tag_layout.addWidget(QLabel(tr("no_tags_configured")), 0, 0)
            return
        columns = 4
        row = col = 0
        for code, desc in self.tags_info.items():
            cb = QCheckBox(f"{code}: {desc}")
            cb.setProperty("code", code)
            cb.stateChanged.connect(lambda state, c=code: self.tagToggled.emit(c, state))
            self.tag_layout.addWidget(cb, row, col)
            self.checkbox_map[code] = cb
            col += 1
            if col >= columns:
                col = 0
                row += 1
