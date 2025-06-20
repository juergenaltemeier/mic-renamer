import os
import re
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QPushButton, QSlider, QFileDialog, QMessageBox, QToolBar,
    QApplication, QLabel, QComboBox,
    QProgressDialog, QDialog, QDialogButtonBox,
    QStyle, QTableWidget, QTableWidgetItem
)
from PySide6.QtGui import QColor, QAction, QIcon
from PySide6.QtCore import Qt, QTimer

from .. import config_manager
from ..utils.i18n import tr, set_language
from .settings_dialog import SettingsDialog
from .theme import resource_icon
from .panels import (
    MediaViewer,
    AspectRatioWidget,
    DragDropTableWidget,
    TagPanel,
)
from .rename_options_dialog import RenameOptionsDialog
from .project_number_input import ProjectNumberInput
from ..logic.settings import ItemSettings
from ..logic.renamer import Renamer
from ..logic.tag_usage import increment_tags
from ..logic.undo_manager import UndoManager


ROLE_SETTINGS = Qt.UserRole + 1
MODE_NORMAL = "normal"
MODE_POSITION = "position"

class RenamerApp(QWidget):
    def __init__(self, state_manager=None):
        super().__init__()
        self.state_manager = state_manager
        self.undo_manager = UndoManager()
        self.rename_mode = MODE_NORMAL
        self.setWindowTitle(tr("app_title"))

        main_layout = QVBoxLayout(self)

        self.toolbar = QToolBar()
        self.setup_toolbar()
        main_layout.addWidget(self.toolbar)

        # no separate selected file display

        # main splitter between preview and table
        self.splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.splitter)

        viewer_widget = QWidget()
        viewer_layout = QVBoxLayout(viewer_widget)

        viewer_toolbar = QHBoxLayout()
        btn_fit = QPushButton("Fit")
        btn_fit.clicked.connect(lambda: self.image_viewer.zoom_fit())
        viewer_toolbar.addWidget(btn_fit)
        btn_prev = QPushButton("←")
        btn_prev.clicked.connect(self.goto_previous_item)
        viewer_toolbar.addWidget(btn_prev)
        btn_next = QPushButton("→")
        btn_next.clicked.connect(self.goto_next_item)
        viewer_toolbar.addWidget(btn_next)
        btn_rot_left = QPushButton("⟲")
        btn_rot_left.clicked.connect(lambda: self.image_viewer.rotate_left())
        viewer_toolbar.addWidget(btn_rot_left)
        btn_rot_right = QPushButton("⟳")
        btn_rot_right.clicked.connect(lambda: self.image_viewer.rotate_right())
        viewer_toolbar.addWidget(btn_rot_right)
        viewer_layout.addLayout(viewer_toolbar)

        self.image_viewer = MediaViewer()
        ar_widget = AspectRatioWidget()
        ar_widget.setWidget(self.image_viewer)
        viewer_layout.addWidget(ar_widget, 5)

        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(10)
        self.zoom_slider.setMaximum(500)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setTickInterval(10)
        self.zoom_slider.setTickPosition(QSlider.TicksBelow)
        self.zoom_slider.valueChanged.connect(self.on_zoom_slider_changed)
        viewer_layout.addWidget(self.zoom_slider)

        self.table_widget = DragDropTableWidget()
        self._ignore_table_changes = False
        self.table_widget.itemChanged.connect(self.on_table_item_changed)
        self.table_widget.pathsAdded.connect(lambda _: self.update_status())

        self.splitter.addWidget(viewer_widget)
        self.splitter.addWidget(self.table_widget)

        if self.state_manager:
            sizes = self.state_manager.get("splitter_sizes")
            if sizes:
                self.splitter.setSizes(sizes)

        # Tag container spanning both columns with manual toggle
        self.tag_panel = TagPanel()
        self.tag_panel.tagToggled.connect(self.on_tag_toggled)
        self.btn_toggle_tags = QPushButton()
        self.btn_toggle_tags.clicked.connect(self.toggle_tag_panel)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.btn_toggle_tags)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)
        main_layout.addWidget(self.tag_panel)
        self.lbl_status = QLabel()
        main_layout.addWidget(self.lbl_status)
        visible = config_manager.get("tag_panel_visible", False)
        self.tag_panel.setVisible(visible)
        self.btn_toggle_tags.setText(tr("hide_tags") if visible else tr("show_tags"))
        
        # Initial deaktivieren
        self.set_item_controls_enabled(False)
        self.table_widget.itemSelectionChanged.connect(self.on_table_selection_changed)

        self.status_message = ""
        self.update_translations()
        self.status_message = ""
        self.update_status()

    def set_splitter_sizes(self, sizes: list[int] | None) -> None:
        """Set the splitter sizes if a valid list is provided."""
        if sizes:
            self.splitter.setSizes(sizes)

    def toggle_tag_panel(self):
        visible = self.tag_panel.isVisible()
        new_visible = not visible
        self.tag_panel.setVisible(new_visible)
        self.btn_toggle_tags.setText(tr("hide_tags") if new_visible else tr("show_tags"))
        config_manager.set("tag_panel_visible", new_visible)

    def rebuild_tag_checkboxes(self):
        self.tag_panel.rebuild()

    def setup_toolbar(self):
        tb = self.toolbar
        style = config_manager.get("toolbar_style", "icons")
        self.toolbar_actions = []
        self.toolbar_action_icons = []

        # actions collected in the "Add" menu
        icon_add_files = resource_icon("file-plus.svg")
        act_add_files = QAction(icon_add_files, tr("add_files"), self)
        act_add_files.setToolTip(tr("add_files"))
        act_add_files.triggered.connect(self.add_files_dialog)
        self.toolbar_actions.append(act_add_files)
        self.toolbar_action_icons.append(icon_add_files)

        icon_add_folder = resource_icon("folder-plus.svg")
        act_add_folder = QAction(icon_add_folder, tr("add_folder"), self)
        act_add_folder.setToolTip(tr("add_folder"))
        act_add_folder.triggered.connect(self.add_folder_dialog)
        self.toolbar_actions.append(act_add_folder)
        self.toolbar_action_icons.append(icon_add_folder)

        # create drop-down menu button for adding items
        self.menu_add = QMenu(tr("add_menu"), self)
        self.menu_add.addAction(act_add_files)
        self.menu_add.addAction(act_add_folder)

        self.icon_add_menu = resource_icon("file-plus.svg")
        self.btn_add_menu = QToolButton()
        self.btn_add_menu.setMenu(self.menu_add)
        self.btn_add_menu.setIcon(self.icon_add_menu)
        self.btn_add_menu.setText(tr("add_menu"))
        self.btn_add_menu.setToolTip(tr("add_menu"))
        self.btn_add_menu.setPopupMode(QToolButton.InstantPopup)
        tb.addWidget(self.btn_add_menu)

        tb.addSeparator()

        icon_preview = resource_icon("eye.svg")
        act_preview = QAction(icon_preview, tr("preview_rename"), self)
        act_preview.setToolTip(tr("preview_rename"))
        act_preview.triggered.connect(self.preview_rename)
        tb.addAction(act_preview)
        self.toolbar_actions.append(act_preview)
        self.toolbar_action_icons.append(icon_preview)

        icon_rename = resource_icon("check-circle.svg")
        act_rename = QAction(icon_rename, tr("rename_all"), self)
        act_rename.setToolTip(tr("rename_all"))
        act_rename.triggered.connect(self.direct_rename)
        tb.addAction(act_rename)
        self.toolbar_actions.append(act_rename)
        self.toolbar_action_icons.append(icon_rename)

        icon_rename_sel = resource_icon("check-square.svg")
        act_rename_sel = QAction(icon_rename_sel, tr("rename_selected"), self)
        act_rename_sel.setToolTip(tr("rename_selected"))
        act_rename_sel.triggered.connect(self.direct_rename_selected)
        tb.addAction(act_rename_sel)
        self.toolbar_actions.append(act_rename_sel)
        self.toolbar_action_icons.append(icon_rename_sel)
        tb.addSeparator()


        icon_compress = resource_icon("arrow-down-circle.svg")
        act_compress = QAction(icon_compress, tr("compress"), self)
        act_compress.setToolTip(tr("compress"))
        act_compress.triggered.connect(self.compress_selected)
        tb.addAction(act_compress)
        self.toolbar_actions.append(act_compress)
        self.toolbar_action_icons.append(icon_compress)

        icon_convert = resource_icon("image.svg")
        act_convert = QAction(icon_convert, tr("convert_heic"), self)
        act_convert.setToolTip(tr("convert_heic"))
        act_convert.triggered.connect(self.convert_heic_selected)
        tb.addAction(act_convert)
        self.toolbar_actions.append(act_convert)
        self.toolbar_action_icons.append(icon_convert)
        tb.addSeparator()

        icon_undo = resource_icon("rotate-ccw.svg")
        act_undo = QAction(icon_undo, tr("undo_rename"), self)
        act_undo.setToolTip(tr("undo_rename"))
        act_undo.triggered.connect(self.undo_rename)
        tb.addAction(act_undo)
        self.toolbar_actions.append(act_undo)
        self.toolbar_action_icons.append(icon_undo)

        icon_remove_sel = resource_icon("trash-2.svg")
        act_remove_sel = QAction(icon_remove_sel, tr("remove_selected"), self)
        act_remove_sel.setToolTip(tr("remove_selected"))
        act_remove_sel.triggered.connect(self.remove_selected_items)
        tb.addAction(act_remove_sel)
        self.toolbar_actions.append(act_remove_sel)
        self.toolbar_action_icons.append(icon_remove_sel)

        icon_clear = resource_icon("trash-2.svg")
        act_clear = QAction(icon_clear, tr("clear_list"), self)
        act_clear.setToolTip(tr("clear_list"))
        act_clear.triggered.connect(self.clear_all)
        tb.addAction(act_clear)
        self.toolbar_actions.append(act_clear)
        self.toolbar_action_icons.append(icon_clear)
        tb.addSeparator()

        icon_settings = resource_icon("settings.svg")
        act_settings = QAction(icon_settings, tr("settings_title"), self)
        act_settings.setToolTip(tr("settings_title"))
        act_settings.triggered.connect(self.open_settings)
        tb.addAction(act_settings)
        self.toolbar_actions.append(act_settings)
        self.toolbar_action_icons.append(icon_settings)

        tb.addSeparator()
        self.combo_mode = QComboBox()
        self.combo_mode.addItem(tr("mode_normal"), MODE_NORMAL)
        self.combo_mode.addItem(tr("mode_position"), MODE_POSITION)
        self.combo_mode.currentIndexChanged.connect(self.on_mode_changed)
        tb.addWidget(self.combo_mode)

        self.lbl_project = QLabel(tr("project_number_label"))
        self.input_project = ProjectNumberInput()
        self.input_project.setText(config_manager.get("last_project_number", ""))
        self.input_project.textChanged.connect(self.save_last_project_number)
        tb.addWidget(self.lbl_project)
        tb.addWidget(self.input_project)

        self.apply_toolbar_style(style)


    def open_settings(self):
        dlg = SettingsDialog(self, state_manager=self.state_manager)
        if dlg.exec() == QDialog.Accepted:
            cfg = config_manager.load()
            set_language(cfg.get("language", "en"))
            self.update_translations()
            self.rebuild_tag_checkboxes()
            style = cfg.get("toolbar_style", "icons")
            self.apply_toolbar_style(style)

    def save_last_project_number(self, text: str) -> None:
        config_manager.set("last_project_number", text.strip())

    def update_translations(self):
        self.setWindowTitle(tr("app_title"))
        actions = self.toolbar_actions
        labels = [
            "add_files", "add_folder", "preview_rename",
            "rename_all", "rename_selected", "compress", "convert_heic",
            "undo_rename", "remove_selected", "clear_list", "settings_title"
        ]
        for action, key in zip(actions, labels):
            action.setText(tr(key))
            action.setToolTip(tr(key))
        # update add menu title and button
        if hasattr(self, "menu_add"):
            self.menu_add.setTitle(tr("add_menu"))
        if hasattr(self, "btn_add_menu"):
            self.btn_add_menu.setText(tr("add_menu"))
            self.btn_add_menu.setToolTip(tr("add_menu"))
        # update form labels
        self.lbl_project.setText(tr("project_number_label"))
        if self.tag_panel.isVisible():
            self.btn_toggle_tags.setText(tr("hide_tags"))
        else:
            self.btn_toggle_tags.setText(tr("show_tags"))
        self.combo_mode.setItemText(0, tr("mode_normal"))
        self.combo_mode.setItemText(1, tr("mode_position"))
        self.update_status()

    def apply_toolbar_style(self, style: str) -> None:
        if style == "text":
            self.toolbar.setToolButtonStyle(Qt.ToolButtonTextOnly)
            for action in self.toolbar_actions:
                action.setIcon(QIcon())
            if hasattr(self, "btn_add_menu"):
                self.btn_add_menu.setIcon(QIcon())
                self.btn_add_menu.setToolButtonStyle(Qt.ToolButtonTextOnly)
        else:
            self.toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)
            for action, icon in zip(self.toolbar_actions, self.toolbar_action_icons):
                action.setIcon(icon)
            if hasattr(self, "btn_add_menu"):
                self.btn_add_menu.setIcon(self.icon_add_menu)
                self.btn_add_menu.setToolButtonStyle(Qt.ToolButtonIconOnly)

    def on_mode_changed(self, index: int) -> None:
        mode = self.combo_mode.itemData(index)
        if mode is None:
            mode = MODE_NORMAL
        self.rename_mode = mode
        self.table_widget.set_mode(mode)

    def add_files_dialog(self):
        exts = " ".join(f"*{e}" for e in ItemSettings.ACCEPT_EXTENSIONS)
        filter_str = f"Images and Videos ({exts})"
        files, _ = QFileDialog.getOpenFileNames(
            self, tr("add_files"), "",
            filter_str
        )
        self.set_status_message(tr("status_loading"))
        self.table_widget.add_paths(files)
        self.set_status_message(None)

    def add_folder_dialog(self):
        folder = QFileDialog.getExistingDirectory(self, tr("add_folder"))
        if folder:
            self.set_status_message(tr("status_loading"))
            entries = os.listdir(folder)
            paths = [
                os.path.join(folder, name)
                for name in entries
                if os.path.isfile(os.path.join(folder, name)) and
                   os.path.splitext(name)[1].lower() in ItemSettings.ACCEPT_EXTENSIONS
            ]
            self.table_widget.add_paths(paths)
            self.set_status_message(None)

    def on_table_selection_changed(self):
        rows = [idx.row() for idx in self.table_widget.selectionModel().selectedRows()]
        if not rows:
            self.image_viewer.load_path("")
            self.zoom_slider.setValue(100)
            self.set_item_controls_enabled(False)
            self.table_widget.sync_check_column()
            self.update_status()
            return

        self.set_item_controls_enabled(True)
        settings_list = []
        for r in rows:
            item0 = self.table_widget.item(r, 1)
            path = item0.data(Qt.UserRole)
            st: ItemSettings = item0.data(ROLE_SETTINGS)
            if st is None:
                st = ItemSettings(path)
                item0.setData(ROLE_SETTINGS, st)
            settings_list.append(st)
        first = settings_list[0]


        if self.rename_mode == MODE_NORMAL:
            intersect = set(settings_list[0].tags)
            union = set(settings_list[0].tags)
            for st in settings_list[1:]:
                intersect &= st.tags
                union |= st.tags
            for code, cb in self.tag_panel.checkbox_map.items():
                desc = self.tag_panel.tags_info.get(code, "")
                cb.blockSignals(True)
                if code in intersect:
                    cb.setTristate(False)
                    cb.setCheckState(Qt.Checked)
                    cb.setText(f"{code}: {desc}")
                elif code in union:
                    cb.setTristate(True)
                    cb.setCheckState(Qt.PartiallyChecked)
                    cb.setText(f"[~] {code}: {desc}")
                else:
                    cb.setTristate(False)
                    cb.setCheckState(Qt.Unchecked)
                    cb.setText(f"{code}: {desc}")
                cb.blockSignals(False)
        
        self.load_preview(first.original_path)
        self.table_widget.sync_check_column()
        self.update_status()

    def save_current_item_settings(self):
        rows = [idx.row() for idx in self.table_widget.selectionModel().selectedRows()]
        if not rows:
            return
        checkbox_states = {code: cb.checkState() for code, cb in self.tag_panel.checkbox_map.items()}
        for row in rows:
            item0 = self.table_widget.item(row, 1)
            settings: ItemSettings = item0.data(ROLE_SETTINGS)
            if settings is None:
                continue
            if self.rename_mode == MODE_NORMAL:
                for code, state in checkbox_states.items():
                    if state == Qt.Checked:
                        settings.tags.add(code)
                    elif state == Qt.Unchecked:
                        settings.tags.discard(code)
                tags_str = ",".join(sorted(settings.tags))
                cell_tags = self.table_widget.item(row, 2)
                cell_date = self.table_widget.item(row, 3)
                cell_suffix = self.table_widget.item(row, 4)
                cell_tags.setText(tags_str)
                cell_tags.setToolTip(tags_str)
                if cell_date:
                    cell_date.setText(settings.date)
                    cell_date.setToolTip(settings.date)
                cell_suffix.setText(settings.suffix)
                cell_suffix.setToolTip(settings.suffix)
            else:
                cell_pos = self.table_widget.item(row, 2)
                cell_suffix = self.table_widget.item(row, 4)
                settings.position = cell_pos.text().strip() if cell_pos else ""
                settings.suffix = cell_suffix.text().strip() if cell_suffix else ""
                if cell_pos:
                    cell_pos.setToolTip(settings.position)
                if cell_suffix:
                    cell_suffix.setToolTip(settings.suffix)
            self.update_row_background(row, settings)
        self.table_widget.sync_check_column()

    def on_tag_toggled(self, code: str, state: int) -> None:
        """Apply tag changes from the tag panel to all selected rows immediately.

        ``state`` may come from ``QCheckBox.stateChanged`` which provides an
        ``int`` rather than ``Qt.CheckState``. Convert it to ensure robust
        comparisons.
        """
        if self.rename_mode != MODE_NORMAL:
            return
        rows = [idx.row() for idx in self.table_widget.selectionModel().selectedRows()]
        if not rows:
            return
        check_state = Qt.CheckState(state)
        for row in rows:
            item0 = self.table_widget.item(row, 1)
            if not item0:
                continue
            settings: ItemSettings = item0.data(ROLE_SETTINGS)
            if settings is None:
                settings = ItemSettings(item0.data(Qt.UserRole))
                item0.setData(ROLE_SETTINGS, settings)
            if check_state in (Qt.Checked, Qt.PartiallyChecked):
                settings.tags.add(code)
            elif check_state == Qt.Unchecked:
                settings.tags.discard(code)
            tags_str = ",".join(sorted(settings.tags))
            cell_tags = self.table_widget.item(row, 2)
            self._ignore_table_changes = True
            try:
                cell_tags.setText(tags_str)
            finally:
                self._ignore_table_changes = False
            cell_tags.setToolTip(tags_str)
            self.update_row_background(row, settings)
        self.table_widget.sync_check_column()
        QTimer.singleShot(0, self.on_table_selection_changed)

    def update_row_background(self, row: int, settings: ItemSettings):
        for col in range(self.table_widget.columnCount()):
            item = self.table_widget.item(row, col)
            if not item:
                continue
            has_info = settings and (
                settings.suffix or
                (settings.tags if self.rename_mode == MODE_NORMAL else settings.position)
            )
            if has_info:
                item.setBackground(QColor('#335533'))
                item.setForeground(QColor('#ffffff'))
            else:
                item.setBackground(QColor(30, 30, 30))
                item.setForeground(QColor(220, 220, 220))

    def on_table_item_changed(self, item: QTableWidgetItem):
        if self._ignore_table_changes:
            return
        row = item.row()
        col = item.column()
        valid_cols = (2, 3, 4) if self.rename_mode == MODE_NORMAL else (2, 4)
        if col not in valid_cols:
            return
        item0 = self.table_widget.item(row, 1)
        if not item0:
            return
        settings: ItemSettings = item0.data(ROLE_SETTINGS)
        if settings is None:
            return
        if self.rename_mode == MODE_NORMAL and col == 2:
            raw_tags = {t.strip() for t in item.text().split(',') if t.strip()}
            valid_tags = {t for t in raw_tags if t in self.tag_panel.tags_info}
            invalid = raw_tags - valid_tags
            if invalid:
                QMessageBox.warning(self, "Invalid Tags",
                                    "Invalid tags: " + ", ".join(sorted(invalid)))
            settings.tags = valid_tags
            text = ",".join(sorted(valid_tags))
            if text != item.text():
                self._ignore_table_changes = True
                item.setText(text)
                self._ignore_table_changes = False
            item.setToolTip(text)
            rows = getattr(self.table_widget, "_selection_before_edit", [])
            for r in rows:
                if r == row:
                    continue
                cell = self.table_widget.item(r, 2)
                if not cell or cell.text().strip():
                    continue
                other_item0 = self.table_widget.item(r, 1)
                other_settings: ItemSettings | None = (
                    other_item0.data(ROLE_SETTINGS) if other_item0 else None
                )
                if other_settings is None:
                    continue
                self._ignore_table_changes = True
                try:
                    cell.setText(text)
                finally:
                    self._ignore_table_changes = False
                cell.setToolTip(text)
                other_settings.tags = set(valid_tags)
                self.update_row_background(r, other_settings)
            self.table_widget._selection_before_edit = []
        elif self.rename_mode == MODE_NORMAL and col == 3:
            text = item.text().strip()
            if not re.fullmatch(r"\d{6}", text):
                QMessageBox.warning(self, "Invalid Date", "Date must be YYMMDD")
                self._ignore_table_changes = True
                item.setText(settings.date)
                self._ignore_table_changes = False
            else:
                settings.date = text
                item.setToolTip(settings.date)
        elif col == 2:
            settings.position = item.text().strip()
            item.setToolTip(settings.position)
        elif col == 4:
            new_suffix = item.text().strip()
            settings.suffix = new_suffix
            item.setToolTip(settings.suffix)
            rows = getattr(self.table_widget, "_selection_before_edit", [])
            for r in rows:
                if r == row:
                    continue
                cell = self.table_widget.item(r, 4)
                if not cell or cell.text().strip():
                    continue
                other_item0 = self.table_widget.item(r, 1)
                other_settings: ItemSettings | None = (
                    other_item0.data(ROLE_SETTINGS) if other_item0 else None
                )
                if other_settings is None:
                    continue
                self._ignore_table_changes = True
                try:
                    cell.setText(new_suffix)
                finally:
                    self._ignore_table_changes = False
                cell.setToolTip(new_suffix)
                other_settings.suffix = new_suffix
                self.update_row_background(r, other_settings)
            self.table_widget._selection_before_edit = []
        self.update_row_background(row, settings)
        if row in {idx.row() for idx in self.table_widget.selectionModel().selectedRows()}:
            self.on_table_selection_changed()

    def load_preview(self, path: str):
        self.image_viewer.load_path(path)
        self.image_viewer.zoom_fit()
        self.zoom_slider.setValue(self.image_viewer.zoom_pct)

    def on_zoom_slider_changed(self, value: int):
        self.image_viewer.zoom_pct = value
        self.image_viewer.apply_transformations()

    def goto_previous_item(self):
        row = self.table_widget.currentRow()
        if row > 0:
            self.table_widget.selectRow(row - 1)

    def goto_next_item(self):
        row = self.table_widget.currentRow()
        if row < self.table_widget.rowCount() - 1:
            self.table_widget.selectRow(row + 1)

    def set_item_controls_enabled(self, enabled: bool):
        for cb in self.tag_panel.checkbox_map.values():
            cb.setEnabled(enabled)

    def clear_all(self):
        self.table_widget.setRowCount(0)
        self.image_viewer.load_path("")
        self.zoom_slider.setValue(100)
        for cb in self.tag_panel.checkbox_map.values():
            cb.setChecked(False)
        self.set_item_controls_enabled(False)
        self.update_status()

    def undo_rename(self):
        if not self.undo_manager.has_history():
            QMessageBox.information(self, tr("undo_nothing_title"), tr("undo_nothing_msg"))
            return
        undone = self.undo_manager.undo_all()
        for row, orig in undone:
            if 0 <= row < self.table_widget.rowCount():
                item0 = self.table_widget.item(row, 1)
                if item0:
                    item0.setText(os.path.basename(orig))
                    item0.setData(Qt.UserRole, orig)
        QMessageBox.information(self, tr("done"), tr("undo_done"))

    def remove_selected_items(self):
        rows = sorted({idx.row() for idx in self.table_widget.selectionModel().selectedRows()}, reverse=True)
        for row in rows:
            self.table_widget.removeRow(row)
        if self.table_widget.rowCount() == 0:
            self.image_viewer.load_path("")
            self.zoom_slider.setValue(100)
            self.set_item_controls_enabled(False)
        else:
            new_row = min(rows[0], self.table_widget.rowCount() - 1)
            self.table_widget.selectRow(new_row)
        self.update_status()

    def compress_selected(self):
        rows = [idx.row() for idx in self.table_widget.selectionModel().selectedRows()]
        if not rows:
            return
        paths = []
        videos = []
        heic_paths = []
        for row in rows:
            item0 = self.table_widget.item(row, 1)
            if not item0:
                continue
            path = item0.data(Qt.UserRole)
            ext = os.path.splitext(path)[1].lower()
            if ext in MediaViewer.VIDEO_EXTS:
                videos.append(path)
                continue
            if ext == ".heic":
                heic_paths.append(path)
            paths.append((row, path))
        if videos:
            QMessageBox.warning(self, tr("video_unsupported"), tr("video_unsupported_msg"))
        if not paths:
            return
        convert_heic = False
        if heic_paths:
            reply = QMessageBox.question(
                self,
                tr("heic_convert_title"),
                tr("heic_convert_msg"),
                QMessageBox.Yes | QMessageBox.No,
            )
            convert_heic = reply == QMessageBox.Yes
        from .compression_dialog import CompressionDialog
        dlg = CompressionDialog(paths, convert_heic, parent=self)
        if dlg.exec() == QDialog.Accepted:
            for row, new_path, size_bytes, compressed_bytes in dlg.results:
                item0 = self.table_widget.item(row, 1)
                item0.setData(Qt.UserRole, new_path)
                item0.setText(os.path.basename(new_path))
                st: ItemSettings = item0.data(ROLE_SETTINGS)
                if st:
                    st.size_bytes = size_bytes
                    st.compressed_bytes = compressed_bytes

    def convert_heic_selected(self):
        rows = [idx.row() for idx in self.table_widget.selectionModel().selectedRows()]
        if not rows:
            return
        from ..logic.heic_converter import convert_heic
        current = self.table_widget.currentRow()
        for row in rows:
            item0 = self.table_widget.item(row, 1)
            if not item0:
                continue
            path = item0.data(Qt.UserRole)
            new_path = convert_heic(path)
            if new_path == path:
                continue
            item0.setData(Qt.UserRole, new_path)
            item0.setText(os.path.basename(new_path))
            size = os.path.getsize(new_path)
            st: ItemSettings = item0.data(ROLE_SETTINGS)
            if st:
                st.size_bytes = size
                st.compressed_bytes = size
            if row == current:
                self.load_preview(new_path)

    def build_rename_mapping(self, dest_dir: str | None = None, rows: list[int] | None = None):
        project = self.input_project.text().strip()
        if not re.fullmatch(r"C\d{6}", project):
            QMessageBox.warning(self, tr("missing_project"), tr("missing_project_msg"))
            return None
        if rows is None:
            n = self.table_widget.rowCount()
            row_iter = range(n)
        else:
            row_iter = rows
        if not row_iter:
            QMessageBox.information(self, tr("no_files"), tr("no_files_msg"))
            return None
        self.save_current_item_settings()
        items = []
        for row in row_iter:
            item0 = self.table_widget.item(row, 1)
            path = item0.data(Qt.UserRole)
            settings: ItemSettings = item0.data(ROLE_SETTINGS)
            if settings is None:
                settings = ItemSettings(path)
                item0.setData(ROLE_SETTINGS, settings)
            settings.original_path = path
            if self.rename_mode == MODE_NORMAL:
                cell_date = self.table_widget.item(row, 3)
                if cell_date:
                    settings.date = cell_date.text().strip()
            else:
                cell_pos = self.table_widget.item(row, 2)
                if cell_pos:
                    settings.position = cell_pos.text().strip()
            items.append(settings)
        renamer = Renamer(project, items, dest_dir=dest_dir, mode=self.rename_mode)
        mapping = renamer.build_mapping()
        return mapping

    def choose_save_directory(self) -> str | None:
        reply = QMessageBox.question(
            self,
            tr('use_original_directory'),
            tr('use_original_directory_msg'),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            return None
        directory = QFileDialog.getExistingDirectory(
            self,
            tr('default_save_dir_label'),
            config_manager.get('default_save_directory', '')
        )
        if directory:
            config_manager.set('default_save_directory', directory)
        return directory or None

    def preview_rename(self):
        mapping = self.build_rename_mapping()
        if mapping is None:
            return
        table_mapping = []
        for settings, orig, new in mapping:
            new_name = os.path.basename(new)
            for row in range(self.table_widget.rowCount()):
                item0 = self.table_widget.item(row, 1)
                if item0.data(Qt.UserRole) == orig:
                    table_mapping.append((row, orig, new_name, new))
                    break
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("preview_rename"))
        dlg_layout = QVBoxLayout(dlg)
        tbl = QTableWidget(len(table_mapping), 2, dlg)
        tbl.setHorizontalHeaderLabels(["Current Name", "Proposed New Name"])
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        tbl.setSelectionMode(QTableWidget.NoSelection)
        tbl.setFocusPolicy(Qt.NoFocus)
        for i, (row, orig, new_name, new_path) in enumerate(table_mapping):
            tbl.setItem(i, 0, QTableWidgetItem(os.path.basename(orig)))
            tbl.setItem(i, 1, QTableWidgetItem(new_name))
        tbl.resizeColumnsToContents()
        tbl.resizeRowsToContents()
        tbl.setMinimumWidth(600)
        dlg_layout.addWidget(tbl)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=dlg)
        dlg_layout.addWidget(btns)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        if dlg.exec() == QDialog.Accepted:
            self.execute_rename_with_progress(table_mapping)

    def direct_rename(self):
        self.rename_with_options(None)

    def direct_rename_selected(self):
        rows = [idx.row() for idx in self.table_widget.selectionModel().selectedRows()]
        self.rename_with_options(rows)

    def rename_with_options(self, rows: list[int] | None):
        dlg = RenameOptionsDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        dest = dlg.directory
        if dest:
            config_manager.set('default_save_directory', dest)
        if rows is None:
            rows = list(range(self.table_widget.rowCount()))
        mapping = self.build_rename_mapping(dest, rows)
        if mapping is None:
            return
        table_mapping = []
        for settings, orig, new in mapping:
            new_name = os.path.basename(new)
            for row in rows:
                item0 = self.table_widget.item(row, 1)
                if item0.data(Qt.UserRole) == orig:
                    table_mapping.append((row, orig, new_name, new))
                    break
        self.execute_rename_with_progress(table_mapping)

    def execute_rename_with_progress(self, table_mapping):
        self.set_status_message(tr("renaming_files"))
        total = len(table_mapping)
        progress = QProgressDialog(
            tr("renaming_files"),
            tr("abort"),
            0,
            total,
            self,
        )
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(200)
        progress.setValue(0)
        done = 0
        used_tags = []
        for row, orig, new_name, new_path in table_mapping:
            if progress.wasCanceled():
                break
            try:
                orig_abs = os.path.abspath(orig)
                new_abs = os.path.abspath(new_path)
                if orig_abs != new_abs:
                    os.rename(orig, new_path)
                    item0 = self.table_widget.item(row, 1)
                    item0.setText(os.path.basename(new_path))
                    item0.setData(Qt.UserRole, new_path)
                    settings = item0.data(ROLE_SETTINGS)
                    if settings and self.rename_mode == MODE_NORMAL:
                        used_tags.extend(settings.tags)
                    self.undo_manager.record(row, orig, new_path)
            except Exception as e:
                QMessageBox.warning(
                    self,
                    tr("rename_failed"),
                    f"Fehler beim Umbenennen:\\n{orig}\\n→ {new_path}\\nError: {e}"
                )
            done += 1
            progress.setValue(done)
        progress.close()
        if progress.wasCanceled():
            QMessageBox.information(
                self,
                tr("partial_rename"),
                tr("partial_rename_msg").format(done=done, total=total)
            )
        else:
            QMessageBox.information(self, tr("done"), tr("rename_done"))
            if used_tags and self.rename_mode == MODE_NORMAL:
                increment_tags(used_tags)
                self.tag_panel.rebuild()
        self.set_status_message(None)

    def set_status_message(self, message: str | None) -> None:
        """Display an additional message in the status bar."""
        self.status_message = message or ""
        self.update_status()

    def update_status(self) -> None:
        """Refresh the selection count and optional message."""
        selected = len(self.table_widget.selectionModel().selectedRows())
        total = self.table_widget.rowCount()
        text = tr("status_selected").format(current=selected, total=total)
        if self.status_message:
            text = f"{text} - {self.status_message}"
        self.lbl_status.setText(text)

    def closeEvent(self, event):
        if self.state_manager:
            self.state_manager.set("width", self.width())
            self.state_manager.set("height", self.height())
            self.state_manager.set("splitter_sizes", self.splitter.sizes())
            self.state_manager.save()
        super().closeEvent(event)

