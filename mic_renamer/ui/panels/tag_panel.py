"""Panel showing available tags as checkboxes."""
from PySide6.QtWidgets import QWidget, QGridLayout, QVBoxLayout, QLabel
from ..components import EnterToggleCheckBox
from PySide6.QtCore import Signal
from ..constants import DEFAULT_MARGIN, DEFAULT_SPACING
import logging

from ...logic.tag_loader import load_tags
from ...logic.tag_usage import load_counts
from ...utils.i18n import tr


class TagPanel(QWidget):
    """Panel showing available tags as checkboxes."""

    tagToggled = Signal(str, int)

    def __init__(self, parent=None, tags_info: dict | None = None):
        super().__init__(parent)
        self._log = logging.getLogger(__name__)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            DEFAULT_MARGIN, DEFAULT_MARGIN, DEFAULT_MARGIN, DEFAULT_MARGIN
        )
        layout.setSpacing(DEFAULT_SPACING)
        self.checkbox_container = QWidget()
        self.tag_layout = QGridLayout(self.checkbox_container)
        self.tag_layout.setContentsMargins(
            DEFAULT_MARGIN, DEFAULT_MARGIN, DEFAULT_MARGIN, DEFAULT_MARGIN
        )
        self.tag_layout.setSpacing(DEFAULT_SPACING)
        layout.addWidget(self.checkbox_container)
        self.checkbox_map: dict[str, EnterToggleCheckBox] = {}
        self.tags_info: dict[str, str] | None = tags_info
        self.rebuild()

    def rebuild(self):
        while self.tag_layout.count():
            item = self.tag_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.checkbox_map = {}
        # always reload tags to pick up language or file changes
        tags = load_tags()
        if not isinstance(tags, dict):
            self._log.warning("Invalid tags info, expected dict but got %s", type(tags).__name__)
            tags = {}
        self.tags_info = tags
        if not self.tags_info:
            self.tag_layout.addWidget(QLabel(tr("no_tags_configured")), 0, 0)
            return
        usage = load_counts()
        sorted_tags = sorted(
            self.tags_info.items(), key=lambda kv: usage.get(kv[0], 0), reverse=True
        )
        columns = 5
        rows = (len(sorted_tags) + columns - 1) // columns
        for idx, (code, desc) in enumerate(sorted_tags):
            row = idx % rows
            col = idx // rows
            cb = EnterToggleCheckBox(f"{code.upper()}: {desc}")
            cb.setProperty("code", code.upper())
            cb.stateChanged.connect(
                lambda state, c=code: self.tagToggled.emit(c.upper(), state)
            )
            self.tag_layout.addWidget(cb, row, col)
            self.checkbox_map[code.upper()] = cb
