from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QDialogButtonBox, QComboBox, QTableWidget, QTableWidgetItem,
    QPushButton, QTabWidget, QWidget, QCheckBox
)

from ..utils.state_manager import StateManager

from .. import config_manager
from ..logic.tag_loader import (
    load_tags,
    load_tags_multilang,
    DEFAULT_TAGS_FILE,
    BUNDLED_TAGS_FILE,
)
from ..logic.tag_usage import reset_counts
from ..utils.i18n import tr
from .panels import CompressionSettingsPanel


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

        tabs = QTabWidget()
        layout.addWidget(tabs)

        general = QWidget()
        tabs.addTab(general, tr("settings_title"))
        gen_layout = QVBoxLayout(general)

        lbl_cfg = QLabel(f"{tr('config_path_label')}: {config_manager.config_dir}")
        lbl_cfg.setToolTip(tr('config_path_desc'))
        gen_layout.addWidget(lbl_cfg)

        gen_layout.addWidget(QLabel(tr("accepted_ext_label")))
        self.edit_ext = QLineEdit(", ".join(self.cfg.get("accepted_extensions", [])))
        self.edit_ext.setToolTip(tr("accepted_ext_desc"))
        gen_layout.addWidget(self.edit_ext)

        hl_save = QHBoxLayout()
        lbl_save = QLabel(tr('default_save_dir_label'))
        lbl_save.setToolTip(tr('default_save_dir_desc'))
        hl_save.addWidget(lbl_save)
        self.edit_save_dir = QLineEdit(self.cfg.get('default_save_directory', ''))
        self.edit_save_dir.setToolTip(tr('default_save_dir_desc'))
        btn_browse_save = QPushButton('...')
        btn_browse_save.clicked.connect(self.choose_save_dir)
        hl_save.addWidget(self.edit_save_dir)
        hl_save.addWidget(btn_browse_save)
        gen_layout.addLayout(hl_save)

        hl = QHBoxLayout()
        lbl_lang = QLabel(tr("language_label"))
        lbl_lang.setToolTip(tr("language_desc"))
        hl.addWidget(lbl_lang)
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["en", "de"])
        self.combo_lang.setToolTip(tr("language_desc"))
        current_lang = self.cfg.get("language", "en")
        index = self.combo_lang.findText(current_lang)
        if index >= 0:
            self.combo_lang.setCurrentIndex(index)
        hl.addWidget(self.combo_lang)
        gen_layout.addLayout(hl)

        hl_theme = QHBoxLayout()
        lbl_theme = QLabel(tr("theme_label"))
        lbl_theme.setToolTip(tr("theme_desc"))
        hl_theme.addWidget(lbl_theme)
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["dark", "light"])
        self.combo_theme.setToolTip(tr("theme_desc"))
        current_theme = self.cfg.get("theme", "dark")
        index = self.combo_theme.findText(current_theme)
        if index >= 0:
            self.combo_theme.setCurrentIndex(index)
        hl_theme.addWidget(self.combo_theme)
        gen_layout.addLayout(hl_theme)

        self.chk_toolbar_text = QCheckBox(tr("use_text_menu"))
        self.chk_toolbar_text.setToolTip(tr("use_text_menu_desc"))
        self.chk_toolbar_text.setChecked(
            self.cfg.get("toolbar_style", "icons") == "text"
        )
        gen_layout.addWidget(self.chk_toolbar_text)

        gen_layout.addWidget(QLabel(tr("tags_label")))
        tags = load_tags(language=current_lang)
        self.tbl_tags = QTableWidget(len(tags), 2)
        self.tbl_tags.setHorizontalHeaderLabels(["Code", "Description"])
        for row, (code, desc) in enumerate(tags.items()):
            self.tbl_tags.setItem(row, 0, QTableWidgetItem(code))
            self.tbl_tags.setItem(row, 1, QTableWidgetItem(desc))
        self.tbl_tags.horizontalHeader().setStretchLastSection(True)
        gen_layout.addWidget(self.tbl_tags)

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
        gen_layout.addLayout(hl_buttons)

        self.compression_panel = CompressionSettingsPanel(self.cfg)
        tabs.addTab(self.compression_panel, tr("compression_settings"))

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

    def choose_save_dir(self):
        from PySide6.QtWidgets import QFileDialog
        dir_path = QFileDialog.getExistingDirectory(self, tr('default_save_dir_label'), self.edit_save_dir.text() or str(config_manager.get('default_save_directory', '')))
        if dir_path:
            self.edit_save_dir.setText(dir_path)

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
        self.cfg['theme'] = self.combo_theme.currentText()
        self.cfg['default_save_directory'] = self.edit_save_dir.text().strip()
        style = 'text' if self.chk_toolbar_text.isChecked() else 'icons'
        self.cfg['toolbar_style'] = style
        config_manager.set('toolbar_style', style)
        self.compression_panel.update_cfg()
        config_manager.save(self.cfg)
        # save tags for selected language
        lang = self.combo_lang.currentText()
        tags_all = load_tags_multilang()
        for row in range(self.tbl_tags.rowCount()):
            code_item = self.tbl_tags.item(row, 0)
            desc_item = self.tbl_tags.item(row, 1)
            if code_item and desc_item:
                code = code_item.text().strip()
                desc = desc_item.text().strip()
                if code:
                    entry = tags_all.get(code, {})
                    if not isinstance(entry, dict):
                        entry = {lang: desc}
                    else:
                        entry[lang] = desc
                    tags_all[code] = entry
        with open(DEFAULT_TAGS_FILE, 'w', encoding='utf-8') as f:
            import json
            json.dump(tags_all, f, indent=2, ensure_ascii=False)
        super().accept()

    def remove_selected_tag_row(self):
        selected = [idx.row() for idx in self.tbl_tags.selectionModel().selectedRows()]
        for row in sorted(selected, reverse=True):
            self.tbl_tags.removeRow(row)

    def reset_usage(self):
        """Reset stored tag usage statistics."""
        reset_counts()

    def restore_defaults(self):
        from PySide6.QtWidgets import QMessageBox, QApplication
        import shutil
        from pathlib import Path

        title = tr("restore_defaults")
        msg = (
            "This will delete all application settings and reset to factory defaults. "
            "The application will now close and must be restarted. Continue?"
        )
        reply = QMessageBox.question(
            self, title, msg, QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        config_path = Path(config_manager.config_dir)
        try:
            if config_path.exists():
                shutil.rmtree(config_path)
        except Exception as e:
            QMessageBox.warning(self, title, f"Failed to reset settings: {e}")
            return
        QMessageBox.information(
            self,
            title,
            "Factory defaults restored. The application will now exit. Please restart.",
        )
        QApplication.instance().quit()

    def closeEvent(self, event):
        if self.state_manager:
            self.state_manager.set("settings_width", self.width())
            self.state_manager.set("settings_height", self.height())
            self.state_manager.save()
        super().closeEvent(event)

