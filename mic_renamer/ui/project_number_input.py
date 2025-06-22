"""Input widget for project numbers like C123456 using individual digit boxes."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QToolButton,
    QStyle,
)
from PySide6.QtCore import Qt, Signal
import re

from .constants import DEFAULT_MARGIN, DEFAULT_SPACING


class DigitEdit(QLineEdit):
    """Single digit editor that selects its text on focus."""

    def focusInEvent(self, event) -> None:  # noqa: D401
        """Select the digit when the field gains focus."""
        super().focusInEvent(event)
        self.selectAll()


class ProjectNumberInput(QWidget):
    """Widget for entering project numbers as ``C`` followed by six digits."""

    textChanged = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            DEFAULT_MARGIN, DEFAULT_MARGIN, DEFAULT_MARGIN, DEFAULT_MARGIN
        )
        layout.setSpacing(DEFAULT_SPACING)
        self._digits: list[DigitEdit] = []
        self.prefix = QLabel(" C")
        layout.addWidget(self.prefix)
        self.setMaximumWidth(160)
        for i in range(6):
            edit = DigitEdit()
            edit.setMaxLength(1)
            edit.setFixedWidth(20)
            edit.setAlignment(Qt.AlignCenter)
            edit.setObjectName(f"digit_{i}")
            edit.textChanged.connect(lambda _=None, idx=i: self._on_digit_changed(idx))
            self._digits.append(edit)
            layout.addWidget(edit)
        self.btn_clear = QToolButton()
        self.btn_clear.setIcon(self.style().standardIcon(QStyle.SP_DialogResetButton))
        self.btn_clear.setToolTip("Clear")
        self.btn_clear.clicked.connect(self.clear)
        layout.addWidget(self.btn_clear)
        self.setFocusProxy(self._digits[0])

    # public API ----------------------------------------------------------
    def text(self) -> str:
        digits = ''.join(d.text() for d in self._digits)
        return f"C{digits}"

    def setText(self, text: str) -> None:  # noqa: N802
        digits = re.sub(r"\D", "", text)[:6]
        for i, d in enumerate(self._digits):
            d.blockSignals(True)
            d.setText(digits[i] if i < len(digits) else "")
            d.blockSignals(False)
        if digits:
            self._focus_next(len(digits) - 1)
        else:
            self._digits[0].setFocus()
            self._digits[0].selectAll()
        self.textChanged.emit(self.text())

    def clear(self) -> None:
        self.setText("")

    # internals -----------------------------------------------------------
    def _on_digit_changed(self, idx: int) -> None:
        text = self._digits[idx].text()
        if text:
            self._focus_next(idx)
        self.textChanged.emit(self.text())

    def _focus_next(self, idx: int) -> None:
        if idx < len(self._digits) - 1:
            self._digits[idx + 1].setFocus()
            self._digits[idx + 1].selectAll()

    def keyPressEvent(self, event) -> None:  # noqa: D401
        """Handle backspace navigation between digit boxes."""
        if event.key() == Qt.Key_Backspace:
            for idx, edit in enumerate(self._digits):
                if edit.hasFocus():
                    if edit.text():
                        edit.clear()
                        if idx > 0:
                            self._digits[idx - 1].setFocus()
                            self._digits[idx - 1].selectAll()
                    else:
                        if idx > 0:
                            prev = self._digits[idx - 1]
                            prev.setFocus()
                            if prev.text():
                                prev.clear()
                            prev.selectAll()
                    self.textChanged.emit(self.text())
                    return
        super().keyPressEvent(event)
