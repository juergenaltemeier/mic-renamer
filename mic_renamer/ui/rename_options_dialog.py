"""Dialog to collect rename options."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QRadioButton,
    QLineEdit, QPushButton, QFileDialog, QDialogButtonBox,
    QCheckBox,
)

from .. import config_manager
from ..utils.i18n import tr


class RenameOptionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("rename_options_title"))
        layout = QVBoxLayout(self)

        self.radio_orig = QRadioButton(tr("use_original_directory"))
        self.radio_orig.setChecked(True)
        self.radio_custom = QRadioButton(tr("default_save_dir_label"))
        hl = QHBoxLayout()
        self.edit_dir = QLineEdit(config_manager.get("default_save_directory", ""))
        btn_browse = QPushButton("...")
        btn_browse.clicked.connect(self.choose_dir)
        hl.addWidget(self.edit_dir)
        hl.addWidget(btn_browse)
        layout.addWidget(self.radio_orig)
        layout.addWidget(self.radio_custom)
        layout.addLayout(hl)

        self.chk_compress = QCheckBox(tr("compress_after_rename"))
        self.chk_compress.setChecked(config_manager.get("compress_after_rename", False))
        layout.addWidget(self.chk_compress)



        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(btns)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

    def choose_dir(self):
        path = QFileDialog.getExistingDirectory(self, tr("default_save_dir_label"), self.edit_dir.text())
        if path:
            self.edit_dir.setText(path)
            self.radio_custom.setChecked(True)

    @property
    def directory(self) -> str | None:
        if self.radio_orig.isChecked():
            return None
        return self.edit_dir.text().strip() or None

    @property
    def compress_after(self) -> bool:
        return self.chk_compress.isChecked()

