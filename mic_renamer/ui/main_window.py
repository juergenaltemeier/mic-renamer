from __future__ import annotations

import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGridLayout,
    QToolBar,
    QFileDialog,
    QMessageBox,
    QStyle,
    QDialog,
)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Qt

from .panels.image_preview import ImagePreviewPanel
from .panels.file_table import FileTablePanel
from .panels.tag_panel import TagPanel
from .panels.settings_dialog import SettingsDialog
from ..config.config_manager import config_manager
from ..utils.state_manager import state_manager
from ..utils.logging_setup import init_logging
from ..utils.i18n import tr, set_language
from ..logic.settings import ItemSettings
from ..logic.renamer import Renamer


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        init_logging()
        cfg = config_manager
        window_cfg = cfg.get_sub("window")
        self.resize(window_cfg.get("width", 1400), window_cfg.get("height", 800))
        self.setMinimumSize(800, 600)
        set_language(cfg.get("language", "en"))
        self.setWindowTitle(tr("app_title"))
        self.setAutoFillBackground(True)

        layout = QVBoxLayout(self)
        self.toolbar = QToolBar()
        layout.addWidget(self.toolbar)

        grid = QGridLayout()
        layout.addLayout(grid)

        self.preview_panel = ImagePreviewPanel()
        self.table_panel = FileTablePanel()
        self.tag_panel = TagPanel()
        grid.addWidget(self.preview_panel, 0, 0)
        grid.addWidget(self.table_panel, 0, 1)
        grid.addWidget(self.tag_panel, 1, 0, 1, 2)

        self.table_panel.selectionModel().currentRowChanged.connect(
            self.on_row_changed
        )

        self.setup_toolbar()
        state_manager.load()
        geo = state_manager.get("geometry")
        if geo:
            self.restoreGeometry(bytes.fromhex(geo))

    def on_row_changed(self, current, previous):
        row = current.row()
        item = self.table_panel.item(row, 1)
        path = item.data(Qt.UserRole) if item else ""
        self.preview_panel.load_image(path)

    def closeEvent(self, event):
        state_manager.set("geometry", self.saveGeometry().toHex().data().decode())
        state_manager.save()
        super().closeEvent(event)

    # Toolbar
    def setup_toolbar(self) -> None:
        style = self.style()
        act_add_files = QAction(style.standardIcon(QStyle.SP_FileIcon), tr("add_files"), self)
        act_add_files.triggered.connect(self.add_files_dialog)
        self.toolbar.addAction(act_add_files)

        act_add_folder = QAction(style.standardIcon(QStyle.SP_DirOpenIcon), tr("add_folder"), self)
        act_add_folder.triggered.connect(self.add_folder_dialog)
        self.toolbar.addAction(act_add_folder)

        act_settings = QAction(QIcon.fromTheme("preferences-system"), tr("settings_title"), self)
        act_settings.triggered.connect(self.open_settings)
        self.toolbar.addAction(act_settings)

        act_preview = QAction(style.standardIcon(QStyle.SP_FileDialogDetailedView), tr("preview_rename"), self)
        act_preview.triggered.connect(self.preview_rename)
        self.toolbar.addAction(act_preview)

        act_rename = QAction(style.standardIcon(QStyle.SP_DialogApplyButton), tr("rename_all"), self)
        act_rename.triggered.connect(self.rename_all)
        self.toolbar.addAction(act_rename)

    # Rename helpers
    def build_mapping(self) -> tuple[str, list[tuple[ItemSettings, str, str]]] | None:
        from PySide6.QtWidgets import QInputDialog

        project, ok = QInputDialog.getText(self, tr("project_number_label"), tr("project_number_placeholder"))
        if not ok or not project:
            QMessageBox.warning(self, tr("missing_project"), tr("missing_project_msg"))
            return None
        items: list[ItemSettings] = []
        for row in range(self.table_panel.rowCount()):
            fname_item = self.table_panel.item(row, 1)
            if not fname_item:
                continue
            path = fname_item.data(Qt.UserRole)
            suffix = self.table_panel.item(row, 3).text().strip() if self.table_panel.item(row, 3) else ""
            tags_str = self.table_panel.item(row, 2).text() if self.table_panel.item(row, 2) else ""
            tags = {t.strip() for t in tags_str.split(',') if t.strip()}
            tags.update(self.tag_panel.selected_tags())
            items.append(ItemSettings(path, tags, suffix))
        renamer = Renamer(project, items)
        return project, renamer.build_mapping()

    def preview_rename(self) -> None:
        result = self.build_mapping()
        if not result:
            return
        project, mapping = result
        from .preview_dialog import show_preview

        if show_preview(self, mapping):
            Renamer(project, []).execute_rename(mapping, self)
            self.update_table_after_rename(mapping)

    def rename_all(self) -> None:
        result = self.build_mapping()
        if not result:
            return
        project, mapping = result
        if QMessageBox.question(self, tr("confirm_rename"), tr("confirm_rename_msg")) == QMessageBox.Yes:
            Renamer(project, []).execute_rename(mapping, self)
            self.update_table_after_rename(mapping)

    def update_table_after_rename(self, mapping: list[tuple[ItemSettings, str, str]]):
        for _, orig, new in mapping:
            for row in range(self.table_panel.rowCount()):
                item = self.table_panel.item(row, 1)
                if item and item.data(Qt.UserRole) == orig:
                    item.setText(os.path.basename(new))
                    item.setData(Qt.UserRole, new)
                    break

    # Dialogs
    def add_files_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(self, tr("add_files"))
        if files:
            self.table_panel.add_paths(files)

    def add_folder_dialog(self):
        folder = QFileDialog.getExistingDirectory(self, tr("add_folder"))
        if folder:
            exts = ItemSettings.ACCEPT_EXTENSIONS
            paths = [
                str(Path(folder) / f)
                for f in os.listdir(folder)
                if os.path.splitext(f)[1].lower() in exts
            ]
            self.table_panel.add_paths(paths)

    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec() == QDialog.Accepted:
            config_manager.load()
            self.tag_panel.rebuild()


