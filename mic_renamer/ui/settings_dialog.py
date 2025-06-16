from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QDialogButtonBox, QComboBox, QTableWidget, QTableWidgetItem,
    QPushButton
)
from PySide6.QtCore import Qt

from ..utils.state_manager import StateManager

from .. import config_manager
from ..logic.tag_loader import load_tags
from ..logic.tag_usage import reset_counts
from ..utils.i18n import tr


class SettingsDialog(QDialog):
    def __init__(self, parent=None, state_manager: StateManager | None = None):
        super().__init__(parent)
        self.state_manager = state_manager
        self.setWindowTitle(tr("settings_title"))
        self.cfg = config_manager.load().copy()
        layout = QVBoxLayout(self)

        # restore size or use larger defaults
        if self.state_manager:
            width = self.state_manager.get("settings_width", 700)
            height = self.state_manager.get("settings_height", 500)
        else:
            width, height = 700, 500
        self.resize(width, height)

        # accepted extensions
        layout.addWidget(QLabel(tr("accepted_ext_label")))
        self.edit_ext = QLineEdit(", ".join(self.cfg.get("accepted_extensions", [])))
        layout.addWidget(self.edit_ext)

        # language selection
        hl = QHBoxLayout()
        hl.addWidget(QLabel(tr("language_label")))
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["en", "de"])
        current_lang = self.cfg.get("language", "en")
        index = self.combo_lang.findText(current_lang)
        if index >= 0:
            self.combo_lang.setCurrentIndex(index)
        hl.addWidget(self.combo_lang)
        layout.addLayout(hl)

        # tags editor (simple table)
        layout.addWidget(QLabel(tr("tags_label")))
        tags = load_tags()
        self.tbl_tags = QTableWidget(len(tags), 2)
        self.tbl_tags.setHorizontalHeaderLabels(["Code", "Description"])
        for row, (code, desc) in enumerate(tags.items()):
            self.tbl_tags.setItem(row, 0, QTableWidgetItem(code))
            self.tbl_tags.setItem(row, 1, QTableWidgetItem(desc))
        self.tbl_tags.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.tbl_tags)

        hl_buttons = QHBoxLayout()
        btn_add = QPushButton("+")
        btn_add.setToolTip("Add new tag")
        btn_add.clicked.connect(self.add_tag_row)
        hl_buttons.addWidget(btn_add)
        btn_remove = QPushButton("-")
        btn_remove.setToolTip("Remove selected tag")
        btn_remove.clicked.connect(self.remove_selected_tag_row)
        hl_buttons.addWidget(btn_remove)
        hl_buttons.addStretch()
        layout.addLayout(hl_buttons)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_restore = QPushButton(tr("restore_defaults"))
        btns.addButton(btn_restore, QDialogButtonBox.ResetRole)
        btn_restore.clicked.connect(self.restore_defaults)
        btn_reset_usage = QPushButton(tr("reset_tag_usage"))
        btns.addButton(btn_reset_usage, QDialogButtonBox.ResetRole)
        btn_reset_usage.clicked.connect(self.reset_usage)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def add_tag_row(self):
        row = self.tbl_tags.rowCount()
        self.tbl_tags.insertRow(row)
        self.tbl_tags.setItem(row, 0, QTableWidgetItem(""))
        self.tbl_tags.setItem(row, 1, QTableWidgetItem(""))

    def accept(self):
        # save extensions
        exts = [e.strip() for e in self.edit_ext.text().split(',') if e.strip()]
        self.cfg['accepted_extensions'] = exts
        # save language
        self.cfg['language'] = self.combo_lang.currentText()
        config_manager.save(self.cfg)
        # save tags
        tags = {}
        for row in range(self.tbl_tags.rowCount()):
            code_item = self.tbl_tags.item(row, 0)
            desc_item = self.tbl_tags.item(row, 1)
            if code_item and desc_item:
                code = code_item.text().strip()
                desc = desc_item.text().strip()
                if code:
                    tags[code] = desc
        # store tags file
        from ..logic.tag_loader import DEFAULT_TAGS_FILE
        with open(DEFAULT_TAGS_FILE, 'w', encoding='utf-8') as f:
            import json
            json.dump(tags, f, indent=2)
        super().accept()

    def remove_selected_tag_row(self):
        selected = [idx.row() for idx in self.tbl_tags.selectionModel().selectedRows()]
        for row in sorted(selected, reverse=True):
            self.tbl_tags.removeRow(row)

    def reset_usage(self):
        """Reset stored tag usage statistics."""
        reset_counts()

    def restore_defaults(self):
        self.cfg = config_manager.restore_defaults()
        from ..logic.tag_loader import BUNDLED_TAGS_FILE, restore_default_tags
        restore_default_tags()
        self.edit_ext.setText(", ".join(self.cfg.get("accepted_extensions", [])))
        lang = self.cfg.get("language", "en")
        idx = self.combo_lang.findText(lang)
        if idx >= 0:
            self.combo_lang.setCurrentIndex(idx)
        tags = load_tags(BUNDLED_TAGS_FILE)
        self.tbl_tags.setRowCount(0)
        for code, desc in tags.items():
            row = self.tbl_tags.rowCount()
            self.tbl_tags.insertRow(row)
            self.tbl_tags.setItem(row, 0, QTableWidgetItem(code))
            self.tbl_tags.setItem(row, 1, QTableWidgetItem(desc))

    def closeEvent(self, event):
        if self.state_manager:
            self.state_manager.set("settings_width", self.width())
            self.state_manager.set("settings_height", self.height())
            self.state_manager.save()
        super().closeEvent(event)

