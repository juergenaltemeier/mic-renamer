"""Input widget for project numbers like C123456 using individual digit boxes."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLineEdit,
    QToolButton,
    QLabel,
)
from PySide6.QtCore import Qt, Signal, QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator, QIcon

from .constants import DEFAULT_SPACING
from .theme import resource_icon


class ProjectNumberInput(QWidget):
    """Modern input widget for project numbers like C123456."""

    textChanged = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(DEFAULT_SPACING)

        self.prefix_label = QLabel("C")
        layout.addWidget(self.prefix_label)

        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText("123456")
        self.line_edit.setMinimumWidth(100)
        self.line_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.line_edit)

        self.validation_label = QLabel()
        layout.addWidget(self.validation_label)

        self.btn_clear = QToolButton()
        self.btn_clear.setIcon(resource_icon("clear.svg"))
        self.btn_clear.setToolTip("Clear")
        self.btn_clear.setCursor(Qt.ArrowCursor)
        self.btn_clear.clicked.connect(self.clear)
        self.btn_clear.hide()
        layout.addWidget(self.btn_clear)

        self.validator = QRegularExpressionValidator(QRegularExpression(r"\d{0,6}"))
        self.line_edit.setValidator(self.validator)

        self.setFocusProxy(self.line_edit)

    def _on_text_changed(self, text: str) -> None:
        self.btn_clear.setVisible(bool(text))
        self.validate_input()
        self.textChanged.emit(self.text())

    def validate_input(self) -> bool:
        text = self.line_edit.text()
        is_valid = len(text) == 6 and text.isdigit()

        if is_valid:
            self.validation_label.setPixmap(
                resource_icon("check-circle.svg").pixmap(16, 16)
            )
        else:
            self.validation_label.setPixmap(QIcon().pixmap(16, 16))

        return is_valid

    def text(self) -> str:
        return f"C{self.line_edit.text()}"

    def setText(self, text: str) -> None:
        if text.startswith("C"):
            text = text[1:]
        self.line_edit.setText(text)

    def clear(self) -> None:
        self.line_edit.clear()
