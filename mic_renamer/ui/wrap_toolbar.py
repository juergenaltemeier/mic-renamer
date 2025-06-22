from __future__ import annotations

"""A toolbar widget that wraps its tool buttons using :class:`FlowLayout`."""

from typing import Iterable

from PySide6.QtWidgets import QWidget, QToolButton, QFrame
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, QSize

from .flow_layout import FlowLayout


class WrapToolBar(QWidget):
    """Toolbar-like widget that wraps buttons when space is limited."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = FlowLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)
        self._buttons: list[QToolButton] = []
        self._tool_button_style = Qt.ToolButtonIconOnly
        self._icon_size = QSize(24, 24)

    # basic API -------------------------------------------------------
    def addAction(self, action: QAction) -> QToolButton:  # noqa: D401 - Qt like
        btn = QToolButton()
        btn.setDefaultAction(action)
        btn.setToolButtonStyle(self._tool_button_style)
        btn.setIconSize(self._icon_size)
        self._layout.addWidget(btn)
        self._buttons.append(btn)
        return btn

    def addWidget(self, widget: QWidget) -> None:  # noqa: D401 - Qt like
        self._layout.addWidget(widget)
        if isinstance(widget, QToolButton):
            widget.setToolButtonStyle(self._tool_button_style)
            widget.setIconSize(self._icon_size)
            self._buttons.append(widget)

    def addSeparator(self) -> None:  # noqa: D401 - Qt like
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        self._layout.addWidget(line)

    def actions(self) -> Iterable[QAction]:  # noqa: D401 - Qt like
        return [btn.defaultAction() for btn in self._buttons if btn.defaultAction() is not None]

    # style handling --------------------------------------------------
    def setToolButtonStyle(self, style: Qt.ToolButtonStyle) -> None:  # noqa: D401
        self._tool_button_style = style
        for btn in self._buttons:
            btn.setToolButtonStyle(style)

    def toolButtonStyle(self) -> Qt.ToolButtonStyle:  # noqa: D401
        return self._tool_button_style

    def setIconSize(self, size: QSize) -> None:
        """Set icon size for all buttons."""
        self._icon_size = size
        for btn in self._buttons:
            btn.setIconSize(size)

    def iconSize(self) -> QSize:
        """Return current icon size."""
        return self._icon_size
