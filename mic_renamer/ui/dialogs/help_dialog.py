# -*- coding: utf-8 -*-
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
)

from mic_renamer.utils.i18n import tr as _


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("help_title"))
        self.setMinimumSize(600, 400)

        layout = QVBoxLayout(self)
        self.setLayout(layout)

        text_label = QLabel(_("help_content_html"))
        text_label.setWordWrap(True)
        text_label.setTextFormat(Qt.RichText)
        text_label.setOpenExternalLinks(True)
        layout.addWidget(text_label)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)