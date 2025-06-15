from __future__ import annotations

from PySide6.QtWidgets import QWidget, QGridLayout, QCheckBox, QVBoxLayout, QLabel

from ...logic.tag_service import tag_service
from ...utils.i18n import tr


class TagPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.checkbox_map: dict[str, QCheckBox] = {}
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr("select_tags_label")))
        self.container = QWidget()
        self.tag_layout = QGridLayout(self.container)
        self.tag_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.container)
        self.rebuild()

    def selected_tags(self) -> set[str]:
        """Return the set of currently checked tag codes."""
        selected = set()
        for code, cb in self.checkbox_map.items():
            if cb.isChecked():
                selected.add(code)
        return selected

    def rebuild(self) -> None:
        while self.tag_layout.count():
            item = self.tag_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.checkbox_map = {}
        tags = tag_service.all_tags()
        columns = 4
        row = col = 0
        for code, desc in tags.items():
            cb = QCheckBox(f"{code}: {desc}")
            cb.setProperty("code", code)
            self.tag_layout.addWidget(cb, row, col)
            self.checkbox_map[code] = cb
            col += 1
            if col >= columns:
                col = 0
                row += 1

