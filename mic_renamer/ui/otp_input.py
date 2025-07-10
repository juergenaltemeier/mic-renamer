from PySide6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QLabel, QPushButton, QFrame
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QIcon
from importlib import resources


def resource_icon(name: str) -> QIcon:
    """Load an icon from the bundled resources folder."""
    path = resources.files("mic_renamer.resources.icons") / name
    return QIcon(str(path))


class OtpInput(QWidget):
    textChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("OtpInput")
        
        container_layout = QHBoxLayout(self)
        container_layout.setContentsMargins(0, 0, 0, 0)

        frame = QFrame(self)
        frame.setObjectName("OtpFrame")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        container_layout.addWidget(frame)

        self.prefix_label = QLabel("C", self)
        self.prefix_label.setObjectName("OtpPrefix")
        layout.addWidget(self.prefix_label)

        self.line_edits = []
        for i in range(6):
            line_edit = QLineEdit(self)
            line_edit.setObjectName("OtpLineEdit")
            line_edit.setMaxLength(1)
            line_edit.setFixedSize(25, 25)
            line_edit.setAlignment(Qt.AlignCenter)
            line_edit.textChanged.connect(self._on_text_changed)
            line_edit.installEventFilter(self)
            self.line_edits.append(line_edit)
            layout.addWidget(line_edit)
        
        self.validation_label = QLabel(self)
        self.validation_label.setFixedSize(20, 20)
        self.validation_label.setScaledContents(True)
        layout.addWidget(self.validation_label)

        self.clear_button = QPushButton(self)
        self.clear_button.setObjectName("OtpClearButton")
        self.clear_button.setIcon(resource_icon("clear.svg"))
        self.clear_button.setFixedSize(20, 20)
        self.clear_button.clicked.connect(self.clear)
        layout.addWidget(self.clear_button)

        self.setStyleSheet("""
            #OtpFrame {
              border: 1px solid #CCCCCC;
              border-radius: 6px;
            }
            QLineEdit {
              border: none;
              font-size: 16px;
            }
            QLineEdit:focus {
              border: 1px solid #4A90E2;
              border-radius: 3px;
            }
        """)

    def _on_text_changed(self, text):
        sender = self.sender()
        
        if len(text) > 1:
            self.setText(text)
            return

        current_index = self.line_edits.index(sender)
        
        if len(text) == 1:
            if current_index < len(self.line_edits) - 1:
                next_field = self.line_edits[current_index + 1]
                next_field.clear()
                next_field.setFocus()
        
        full_text = self.text()
        self.textChanged.emit(full_text)
        self.update_validation_status(full_text)

    def eventFilter(self, obj, event):
        if event.type() == QKeyEvent.KeyPress:
            key = event.key()
            if obj in self.line_edits:
                current_index = self.line_edits.index(obj)

                if key == Qt.Key_Backspace and not obj.text() and current_index > 0:
                    self.line_edits[current_index - 1].setFocus()
                    self.line_edits[current_index - 1].selectAll()

                elif key == Qt.Key_Left and current_index > 0:
                    self.line_edits[current_index - 1].setFocus()
                
                elif key == Qt.Key_Right and current_index < len(self.line_edits) - 1:
                    self.line_edits[current_index + 1].setFocus()

        elif event.type() == QKeyEvent.MouseButtonPress:
             if obj in self.line_edits:
                obj.clear()

        return super().eventFilter(obj, event)

    def text(self):
        return "C" + "".join([le.text() for le in self.line_edits])

    def setText(self, text):
        for le in self.line_edits:
            le.blockSignals(True)

        if text.startswith("C"):
            text = text[1:]
        
        for le in self.line_edits:
            le.clear()

        for i, char in enumerate(text):
            if i < len(self.line_edits):
                self.line_edits[i].setText(char)

        for le in self.line_edits:
            le.blockSignals(False)
        
        full_text = self.text()
        self.textChanged.emit(full_text)
        self.update_validation_status(full_text)

        last_filled_index = min(len(text) - 1, len(self.line_edits) - 1)
        if last_filled_index < len(self.line_edits) - 1:
            self.line_edits[last_filled_index + 1].setFocus()
        else:
            self.line_edits[last_filled_index].setFocus()

    def clear(self):
        for le in self.line_edits:
            le.clear()
        self.line_edits[0].setFocus()

    def update_validation_status(self, text):
        import re
        if re.fullmatch(r"C\d{6}", text):
            self.validation_label.setPixmap(resource_icon("check-circle.svg").pixmap(20, 20))
        else:
            self.validation_label.clear()


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    widget = OtpInput()
    widget.show()
    sys.exit(app.exec())