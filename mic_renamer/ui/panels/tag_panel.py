"""Panel showing available tags as checkboxes."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QScrollArea
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QKeyEvent
from ..components import TagBox
from ..constants import DEFAULT_MARGIN, DEFAULT_SPACING
from ..flow_layout import FlowLayout
import logging

from ...logic.tag_loader import load_tags
from ...logic.tag_usage import load_counts
from ...utils.i18n import tr


class TagPanel(QWidget):
    """Panel showing available tags as checkboxes."""

    tagToggled = Signal(str, int)
    arrowKeyPressed = Signal(int)

    def __init__(self, parent=None, tags_info: dict | None = None):
        super().__init__(parent)
        self._log = logging.getLogger(__name__)
        self._preselected_tag = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            DEFAULT_MARGIN, DEFAULT_MARGIN, DEFAULT_MARGIN, DEFAULT_MARGIN
        )
        layout.setSpacing(DEFAULT_SPACING)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText(tr("search_tags"))
        self.search_bar.textChanged.connect(self._filter_tags)
        self.search_bar.keyPressEvent = self._handle_search_key_press
        layout.addWidget(self.search_bar)

        self.checkbox_container = QWidget()
        self.tag_layout = FlowLayout(self.checkbox_container)
        # Remove margins and spacing to fit more tags tightly
        self.tag_layout.setContentsMargins(0, 0, 0, 0)
        self.tag_layout.setSpacing(0)
        # Wrap tag container in a scroll area for overflow
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.checkbox_container)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        layout.addWidget(self.scroll_area)
        self.checkbox_map: dict[str, TagBox] = {}
        self.tags_info: dict[str, str] | None = tags_info
        self.rebuild()

    def _handle_search_key_press(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self._preselected_tag:
                self._preselected_tag.toggle()
            event.accept()
        elif event.key() == Qt.Key_Down:
            self.arrowKeyPressed.emit(Qt.Key_Down)
            event.accept()
        elif event.key() == Qt.Key_Up:
            self.arrowKeyPressed.emit(Qt.Key_Up)
            event.accept()
        else:
            QLineEdit.keyPressEvent(self.search_bar, event)

    def _move_preselection(self, direction: int):
        visible_tags = [cb for cb in self.checkbox_map.values() if cb.isVisible()]
        if not visible_tags:
            return

        current_index = -1
        if self._preselected_tag and self._preselected_tag in visible_tags:
            current_index = visible_tags.index(self._preselected_tag)

        new_index = (current_index + direction) % len(visible_tags)
        self._update_preselection(visible_tags[new_index])

    def _update_preselection(self, new_tag: TagBox | None):
        if self._preselected_tag:
            self._preselected_tag.set_preselected(False)
        
        self._preselected_tag = new_tag
        
        if self._preselected_tag:
            self._preselected_tag.set_preselected(True)

    def _filter_tags(self, text: str):
        """Filter checkboxes based on search text."""
        text = text.lower()
        first_visible = None
        for code, checkbox in self.checkbox_map.items():
            description = self.tags_info.get(code, "")
            if text in code.lower() or text in description.lower():
                checkbox.show()
                if first_visible is None:
                    first_visible = checkbox
            else:
                checkbox.hide()
        
        self._update_preselection(first_visible)

    def rebuild(self, language: str | None = None):
        # clear any existing preselection to avoid operating on deleted widgets
        self._preselected_tag = None
        # Clear existing checkboxes from the layout and the map
        for i in reversed(range(self.tag_layout.count())):
            item = self.tag_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                self.tag_layout.removeWidget(widget)
                widget.deleteLater()
        self.checkbox_map.clear()

        # always reload tags to pick up language or file changes
        tags = load_tags(language=language)
        if not isinstance(tags, dict):
            self._log.warning("Invalid tags info, expected dict but got %s", type(tags).__name__)
            tags = {}
        self.tags_info = tags
        if not self.tags_info:
            self.tag_layout.addWidget(QLabel(tr("no_tags_configured")))
            return
        
        usage = load_counts()
        
        # Ensure tags_info is a dictionary before sorting
        tags_info_items = self.tags_info.items() if isinstance(self.tags_info, dict) else []
        
        sorted_tags = sorted(
            tags_info_items, key=lambda kv: usage.get(kv[0], 0), reverse=True
        )
        
        for code, desc in sorted_tags:
            code_upper = code.upper()
            if code_upper in self.checkbox_map:
                # Update existing TagBox
                cb = self.checkbox_map[code_upper]
                cb.set_text(code_upper, desc)
            else:
                # Create new TagBox
                cb = TagBox(code_upper, desc)
                cb.toggled.connect(
                    lambda state, c=code_upper: self.tagToggled.emit(c, state)
                )
                self.tag_layout.addWidget(cb)
                self.checkbox_map[code_upper] = cb

    def retranslate_ui(self, language: str | None = None):
        self.search_bar.setPlaceholderText(tr("search_tags"))
        self.rebuild(language=language)
