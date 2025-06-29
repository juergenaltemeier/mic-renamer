from __future__ import annotations

from PySide6.QtWidgets import QLayout, QWidgetItem, QWidget
from PySide6.QtCore import QRect, QSize, Qt

from .constants import DEFAULT_MARGIN, DEFAULT_SPACING

"""A simple flow layout that arranges child widgets horizontally and wraps."""


class FlowLayout(QLayout):
    """Lay out widgets horizontally and wrap them to new rows when needed."""

    def __init__(
        self,
        parent: QWidget | None = None,
        margin: int = DEFAULT_MARGIN,
        spacing: int | None = DEFAULT_SPACING,
    ) -> None:
        super().__init__(parent)
        self._items: list[QWidgetItem] = []
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        if spacing is not None:
            self.setSpacing(spacing)

    # QLayout API -----------------------------------------------------
    def addItem(self, item: QWidgetItem) -> None:  # noqa: D401 - Qt override
        self._items.append(item)

    def count(self) -> int:  # noqa: D401 - Qt override
        return len(self._items)

    def itemAt(self, index: int) -> QWidgetItem | None:  # noqa: D401 - Qt override
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int) -> QWidgetItem | None:  # noqa: D401 - Qt override
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientations:  # noqa: D401 - Qt override
        return Qt.Orientations(0)

    def hasHeightForWidth(self) -> bool:  # noqa: D401 - Qt override
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: D401 - Qt override
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect: QRect) -> None:  # noqa: D401 - Qt override
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self) -> QSize:  # noqa: D401 - Qt override
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # noqa: D401 - Qt override
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        left, top, right, bottom = self.getContentsMargins()
        size += QSize(left + right, top + bottom)
        return size

    # internal --------------------------------------------------------
    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        x = rect.x()
        y = rect.y()
        line_height = 0

        left, top, right, bottom = self.getContentsMargins()
        effective_rect = rect.adjusted(left, top, -right, -bottom)

        for item in self._items:
            hint = item.sizeHint()
            space_x = self.spacing()
            space_y = self.spacing()
            next_x = x + hint.width() + space_x
            if next_x - space_x > effective_rect.right() and line_height > 0:
                x = effective_rect.x()
                y = y + line_height + space_y
                next_x = x + hint.width() + space_x
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(x, y, hint.width(), hint.height()))
            x = next_x
            line_height = max(line_height, hint.height())

        return y + line_height - rect.y() + top + bottom
