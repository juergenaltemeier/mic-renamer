from __future__ import annotations

import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGridLayout,
    QToolBar,
    QAction,
    QFileDialog,
    QMessageBox,
)
from PySide6.QtGui import QIcon, QStyle
from PySide6.QtCore import Qt

from .panels.image_preview import ImagePreviewPanel
from .panels.file_table import FileTablePanel
from .panels.tag_panel import TagPanel
from .panels.settings_dialog import SettingsDialog
from .theming import theme_manager
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
        theme_manager.apply_palette(self)

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

        self.setup_toolbar()
        state_manager.load()
        geo = state_manager.get("geometry")
        if geo:
            self.restoreGeometry(bytes.fromhex(geo))

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
        if dlg.exec() == dlg.Accepted:
            config_manager.load()
            theme_manager.reload()
            theme_manager.apply_palette(self)
            self.tag_panel.rebuild()


