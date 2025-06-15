"""Panel containing tag checkboxes."""
from PySide6.QtWidgets import QWidget, QGridLayout, QVBoxLayout, QLabel, QCheckBox
from PySide6.QtCore import Qt

from ...logic.tag_loader import load_tags
from ...utils.i18n import tr


class TagPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr("select_tags_label")))
        self.checkbox_container = QWidget()
        self.tag_layout = QGridLayout(self.checkbox_container)
        self.tag_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.checkbox_container)
        self.checkbox_map: dict[str, QCheckBox] = {}
        self.tags_info: dict[str, str] = {}
        self.rebuild()

    def rebuild(self):
        while self.tag_layout.count():
            item = self.tag_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.checkbox_map = {}
        self.tags_info = load_tags()
        columns = 4
        row = col = 0
        for code, desc in self.tags_info.items():
            cb = QCheckBox(f"{code}: {desc}")
            cb.setProperty("code", code)
            self.tag_layout.addWidget(cb, row, col)
            self.checkbox_map[code] = cb
            col += 1
            if col >= columns:
                col = 0
                row += 1
