import os
import re
import logging
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QPushButton, QSlider, QFileDialog, QMessageBox,
    QApplication, QLabel, QComboBox,
    QProgressDialog, QDialog, QDialogButtonBox,
    QStyle, QTableWidget, QTableWidgetItem,
    QMenu, QToolButton, QSizePolicy, QToolBar,
)
from PySide6.QtGui import QColor, QAction, QIcon, QPixmap, QPixmapCache, QImage
from PySide6.QtCore import Qt, QTimer, QSize, QThread, Slot

from .. import config_manager
from ..utils.i18n import tr, set_language
from .settings_dialog import SettingsDialog
from .theme import resource_icon
from .constants import DEFAULT_MARGIN, DEFAULT_SPACING
from .panels import (
    MediaViewer,
    DragDropTableWidget,
    TagPanel,
)
from .rename_options_dialog import RenameOptionsDialog
from .project_number_input import ProjectNumberInput
from ..logic.settings import ItemSettings
from ..logic.renamer import Renamer
from ..logic.image_compressor import ImageCompressor
from ..logic.tag_usage import increment_tags
from ..logic.undo_manager import UndoManager
from .wrap_toolbar import WrapToolBar
from ..utils.workers import Worker, PreviewLoader


ROLE_SETTINGS = Qt.UserRole + 1
MODE_NORMAL = "normal"
MODE_POSITION = "position"
MODE_PA_MAT = "pa_mat"

class RenamerApp(QWidget):
    def __init__(self, state_manager=None):
        super().__init__()
        self.state_manager = state_manager
        self.undo_manager = UndoManager()
        self.rename_mode = MODE_NORMAL
        self._preview_thread: QThread | None = None
        self._preview_loader: PreviewLoader | None = None
        self._rename_thread: QThread | None = None
        self._rename_worker: Worker | None = None
        # for JPEG conversion threads
        self._convert_thread: QThread | None = None
        self._convert_worker: Worker | None = None
        self.setWindowTitle(tr("app_title"))

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(
            DEFAULT_MARGIN, DEFAULT_MARGIN, DEFAULT_MARGIN, DEFAULT_MARGIN
        )
        main_layout.setSpacing(DEFAULT_SPACING)

        self.toolbar = WrapToolBar()
        self.toolbar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.toolbar.setIconSize(QSize(24, 24))
        self.setup_toolbar()
        main_layout.addWidget(self.toolbar)

        # no separate selected file display

        # main splitter between preview and table
        self.splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.splitter, 1)

        viewer_widget = QWidget()
        viewer_layout = QVBoxLayout(viewer_widget)

        self.image_viewer = MediaViewer()

        self.viewer_actions: list[QAction] = []
        self.viewer_buttons: list[QToolButton] = []
        viewer_toolbar = QHBoxLayout()
        icon_size = self.toolbar.iconSize()

        act_zoom_fit = QAction(resource_icon("zoom-fit.svg"), "Fit", self)
        act_zoom_fit.triggered.connect(self.image_viewer.zoom_fit)
        btn_fit = QToolButton()
        btn_fit.setDefaultAction(act_zoom_fit)
        btn_fit.setIconSize(icon_size)
        viewer_toolbar.addWidget(btn_fit)
        self.viewer_actions.append(act_zoom_fit)
        self.viewer_buttons.append(btn_fit)

        act_prev = QAction(resource_icon("prev.svg"), "Prev", self)
        act_prev.triggered.connect(self.goto_previous_item)
        btn_prev = QToolButton()
        btn_prev.setDefaultAction(act_prev)
        btn_prev.setIconSize(icon_size)
        viewer_toolbar.addWidget(btn_prev)
        self.viewer_actions.append(act_prev)
        self.viewer_buttons.append(btn_prev)

        act_next = QAction(resource_icon("next.svg"), "Next", self)
        act_next.triggered.connect(self.goto_next_item)
        btn_next = QToolButton()
        btn_next.setDefaultAction(act_next)
        btn_next.setIconSize(icon_size)
        viewer_toolbar.addWidget(btn_next)
        self.viewer_actions.append(act_next)
        self.viewer_buttons.append(btn_next)

        act_rot_left = QAction(resource_icon("rotate-left.svg"), "Rotate Left", self)
        act_rot_left.triggered.connect(self.image_viewer.rotate_left)
        btn_rot_left = QToolButton()
        btn_rot_left.setDefaultAction(act_rot_left)
        btn_rot_left.setIconSize(icon_size)
        viewer_toolbar.addWidget(btn_rot_left)
        self.viewer_actions.append(act_rot_left)
        self.viewer_buttons.append(btn_rot_left)

        act_rot_right = QAction(resource_icon("rotate-right.svg"), "Rotate Right", self)
        act_rot_right.triggered.connect(self.image_viewer.rotate_right)
        btn_rot_right = QToolButton()
        btn_rot_right.setDefaultAction(act_rot_right)
        btn_rot_right.setIconSize(icon_size)
        viewer_toolbar.addWidget(btn_rot_right)
        self.viewer_actions.append(act_rot_right)
        self.viewer_buttons.append(btn_rot_right)

        viewer_layout.addLayout(viewer_toolbar)
        viewer_layout.addWidget(self.image_viewer, 5)

        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(10)
        self.zoom_slider.setMaximum(500)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setTickInterval(10)
        self.zoom_slider.setTickPosition(QSlider.TicksBelow)
        self.zoom_slider.valueChanged.connect(self.on_zoom_slider_changed)
        viewer_layout.addWidget(self.zoom_slider)

        # table toolbar directly above the table widget
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(
            DEFAULT_MARGIN, DEFAULT_MARGIN, DEFAULT_MARGIN, DEFAULT_MARGIN
        )
        table_layout.setSpacing(DEFAULT_SPACING)

        self.table_toolbar = QToolBar()
        self.table_toolbar.setIconSize(QSize(24, 24))
        self.setup_table_toolbar()
        self.apply_toolbar_style(config_manager.get("toolbar_style", "icons"))
        table_layout.addWidget(self.table_toolbar)

        self.table_widget = DragDropTableWidget()
        self._ignore_table_changes = False
        self.table_widget.itemChanged.connect(self.on_table_item_changed)
        self.table_widget.pathsAdded.connect(lambda _: self.update_status())
        table_layout.addWidget(self.table_widget)

        self.splitter.addWidget(viewer_widget)
        self.splitter.addWidget(table_container)

        if self.state_manager:
            sizes = self.state_manager.get("splitter_sizes")
            if sizes:
                self.splitter.setSizes(sizes)

        # Tag container spanning both columns with manual toggle
        self.tag_panel = TagPanel()
        self.tag_panel.tagToggled.connect(self.on_tag_toggled)
        self.btn_toggle_tags = QPushButton()
        self.btn_toggle_tags.clicked.connect(self.toggle_tag_panel)

        # timer for debouncing heavy selection updates
        self._sel_change_timer = QTimer(self)
        self._sel_change_timer.setSingleShot(True)
        self._sel_change_timer.setInterval(100)
        self._sel_change_timer.timeout.connect(self._apply_selection_change)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.btn_toggle_tags)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)
        main_layout.addWidget(self.tag_panel)
        self.lbl_status = QLabel()
        self.lbl_status.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.lbl_status.setMaximumHeight(
            self.lbl_status.fontMetrics().height() + 4
        )
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
        act_add_files.setToolTip(tr("tip_add_files"))
        act_add_files.triggered.connect(self.add_files_dialog)
        self.toolbar_actions.append(act_add_files)
        self.toolbar_action_icons.append(icon_add_files)

        icon_add_folder = resource_icon("folder-plus.svg")
        act_add_folder = QAction(icon_add_folder, tr("add_folder"), self)
        act_add_folder.setToolTip(tr("tip_add_folder"))
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
        self.btn_add_menu.setToolTip(tr("tip_add_menu"))
        self.btn_add_menu.setPopupMode(QToolButton.InstantPopup)
        tb.addWidget(self.btn_add_menu)

        tb.addSeparator()

        icon_preview = resource_icon("eye.svg")
        act_preview = QAction(icon_preview, tr("preview_rename"), self)
        act_preview.setToolTip(tr("tip_preview_rename"))
        act_preview.triggered.connect(self.preview_rename)
        tb.addAction(act_preview)
        self.toolbar_actions.append(act_preview)
        self.toolbar_action_icons.append(icon_preview)

        tb.addSeparator()


        icon_compress = resource_icon("arrow-down-circle.svg")
        act_compress = QAction(icon_compress, tr("compress"), self)
        act_compress.setToolTip(tr("tip_compress"))
        act_compress.triggered.connect(self.compress_selected)
        tb.addAction(act_compress)
        self.toolbar_actions.append(act_compress)
        self.toolbar_action_icons.append(icon_compress)

        icon_convert = resource_icon("image.svg")
        act_convert = QAction(icon_convert, tr("convert_heic"), self)
        act_convert.setToolTip(tr("tip_convert_heic"))
        act_convert.triggered.connect(self.convert_selected_to_jpeg)
        tb.addAction(act_convert)
        self.toolbar_actions.append(act_convert)
        self.toolbar_action_icons.append(icon_convert)
        tb.addSeparator()

        icon_undo = resource_icon("rotate-ccw.svg")
        act_undo = QAction(icon_undo, tr("undo_rename"), self)
        act_undo.setToolTip(tr("tip_undo_rename"))
        act_undo.triggered.connect(self.undo_rename)
        tb.addAction(act_undo)
        self.toolbar_actions.append(act_undo)
        self.toolbar_action_icons.append(icon_undo)

        icon_remove_sel = resource_icon("trash-2.svg")
        self.act_remove_sel = QAction(icon_remove_sel, tr("remove_selected"), self)
        self.act_remove_sel.setToolTip(tr("tip_remove_selected"))
        self.act_remove_sel.triggered.connect(self.remove_selected_items)
        self.toolbar_actions.append(self.act_remove_sel)
        self.toolbar_action_icons.append(icon_remove_sel)

        icon_clear_suffix = resource_icon("suffix-clear.svg")
        self.act_clear_suffix = QAction(icon_clear_suffix, tr("clear_suffix"), self)
        self.act_clear_suffix.setToolTip(tr("tip_clear_suffix"))
        self.act_clear_suffix.triggered.connect(self.clear_selected_suffixes)
        self.toolbar_actions.append(self.act_clear_suffix)
        self.toolbar_action_icons.append(icon_clear_suffix)

        icon_clear = resource_icon("clear.svg")
        self.act_clear = QAction(icon_clear, tr("clear_list"), self)
        self.act_clear.setToolTip(tr("tip_clear_list"))
        self.act_clear.triggered.connect(self.clear_all)
        self.toolbar_actions.append(self.act_clear)
        self.toolbar_action_icons.append(icon_clear)

        icon_settings = resource_icon("settings.svg")
        act_settings = QAction(icon_settings, tr("settings_title"), self)
        act_settings.setToolTip(tr("tip_settings"))
        act_settings.triggered.connect(self.open_settings)
        tb.addAction(act_settings)
        self.toolbar_actions.append(act_settings)
        self.toolbar_action_icons.append(icon_settings)

        self.lbl_project = QLabel(tr("project_number_label"))
        self.input_project = ProjectNumberInput()
        self.input_project.setText(config_manager.get("last_project_number", ""))
        self.input_project.textChanged.connect(self.save_last_project_number)
        tb.addWidget(self.lbl_project)
        tb.addWidget(self.input_project)


    def setup_table_toolbar(self) -> None:
        """Create toolbar with table-related actions."""
        tb = self.table_toolbar
        tb.addAction(self.act_remove_sel)
        self.act_clear_suffix.setIcon(resource_icon("suffix-clear.svg"))
        tb.addAction(self.act_clear_suffix)
        self.act_clear.setIcon(resource_icon("clear.svg"))
        tb.addAction(self.act_clear)
        tb.addSeparator()
        self.combo_mode = QComboBox()
        self.combo_mode.addItem(tr("mode_normal"), MODE_NORMAL)
        self.combo_mode.addItem(tr("mode_position"), MODE_POSITION)
        self.combo_mode.addItem(tr("mode_pa_mat"), MODE_PA_MAT)
        self.combo_mode.currentIndexChanged.connect(self.on_mode_changed)
        tb.addWidget(self.combo_mode)


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
            "compress", "convert_heic",
            "undo_rename", "remove_selected", "clear_suffix",
            "clear_list", "settings_title"
        ]
        tips = [
            "tip_add_files", "tip_add_folder", "tip_preview_rename",
            "tip_compress", "tip_convert_heic",
            "tip_undo_rename", "tip_remove_selected", "tip_clear_suffix",
            "tip_clear_list", "tip_settings"
        ]
        for action, key, tip in zip(actions, labels, tips):
            action.setText(tr(key))
            action.setToolTip(tr(tip))
        # update add menu title and button
        if hasattr(self, "menu_add"):
            self.menu_add.setTitle(tr("add_menu"))
        if hasattr(self, "btn_add_menu"):
            self.btn_add_menu.setText(tr("add_menu"))
            self.btn_add_menu.setToolTip(tr("tip_add_menu"))
        # update form labels
        self.lbl_project.setText(tr("project_number_label"))
        if self.tag_panel.isVisible():
            self.btn_toggle_tags.setText(tr("hide_tags"))
        else:
            self.btn_toggle_tags.setText(tr("show_tags"))
        self.combo_mode.setItemText(0, tr("mode_normal"))
        self.combo_mode.setItemText(1, tr("mode_position"))
        if self.combo_mode.count() > 2:
            self.combo_mode.setItemText(2, tr("mode_pa_mat"))
        self.update_status()

    def apply_toolbar_style(self, style: str) -> None:
        if style == "text":
            self.toolbar.setToolButtonStyle(Qt.ToolButtonTextOnly)
            self.table_toolbar.setToolButtonStyle(Qt.ToolButtonTextOnly)
            for action in self.toolbar_actions:
                action.setIcon(QIcon())
            if hasattr(self, "btn_add_menu"):
                self.btn_add_menu.setIcon(QIcon())
                self.btn_add_menu.setToolButtonStyle(Qt.ToolButtonTextOnly)
        else:
            self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            self.table_toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            for action, icon in zip(self.toolbar_actions, self.toolbar_action_icons):
                action.setIcon(icon)
            if hasattr(self, "btn_add_menu"):
                self.btn_add_menu.setIcon(self.icon_add_menu)
                self.btn_add_menu.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

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
        if files:
            self._import_paths(files)

    def add_folder_dialog(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            tr("add_folder"),
            config_manager.get('default_import_directory', '')
        )
        if folder:
            entries = os.listdir(folder)
            paths = [
                os.path.join(folder, name)
                for name in entries
                if os.path.isfile(os.path.join(folder, name)) and
                   os.path.splitext(name)[1].lower() in ItemSettings.ACCEPT_EXTENSIONS
            ]
            if paths:
                self._import_paths(paths)

    def _import_paths(self, paths: list[str]) -> None:
        """Import given file paths into the table with a progress dialog."""
        total = len(paths)
        progress = QProgressDialog(
            tr("status_loading"),
            tr("abort"),
            0,
            total,
            self,
        )
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(200)
        progress.setValue(0)
        for idx, path in enumerate(paths, start=1):
            if progress.wasCanceled():
                break
            self.table_widget.add_paths([path])
            progress.setValue(idx)
            QApplication.processEvents()
        progress.close()

    def on_table_selection_changed(self):
        """Start or restart the selection change timer."""
        self._sel_change_timer.start()

    def _apply_selection_change(self):
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
        self.table_widget.setSortingEnabled(False)
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
        self.table_widget.setSortingEnabled(False)
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
                QMessageBox.warning(
                    self,
                    tr("invalid_tags_title"),
                    tr("invalid_tags_msg").format(tags=", ".join(sorted(invalid)))
                )
            settings.tags = valid_tags
            text = ",".join(sorted(valid_tags))
            if text != item.text():
                self._ignore_table_changes = True
                item.setText(text)
                self._ignore_table_changes = False
            item.setToolTip(text)
            rows = getattr(self.table_widget, "_selection_before_edit", [])
            if rows:
                self.table_widget.setSortingEnabled(False)
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
                QMessageBox.warning(
                    self,
                    tr("invalid_date_title"),
                    tr("invalid_date_msg"),
                )
                self._ignore_table_changes = True
                item.setText(settings.date)
                self._ignore_table_changes = False
            else:
                settings.date = text
                item.setToolTip(settings.date)
        elif self.rename_mode == MODE_POSITION and col == 2:
            settings.position = item.text().strip()
            item.setToolTip(settings.position)
        elif self.rename_mode == MODE_PA_MAT and col == 2:
            settings.pa_mat = item.text().strip()
            item.setToolTip(settings.pa_mat)
        elif col == 4:
            new_suffix = item.text().strip()
            settings.suffix = new_suffix
            item.setToolTip(settings.suffix)
            rows = getattr(self.table_widget, "_selection_before_edit", [])
            if rows:
                self.table_widget.setSortingEnabled(False)
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
        """Load preview image/video using a background thread."""
        # cancel running loader
        if self._preview_loader:
            self._preview_loader.stop()
        if self._preview_thread:
            self._preview_thread.quit()
            self._preview_thread.wait()
            self._preview_thread = None
            if self._preview_loader:
                self._preview_loader.deleteLater()
                self._preview_loader = None

        if not path:
            self.image_viewer.load_path("")
            self.zoom_slider.setValue(100)
            return

        # Check if it's a video file - handle directly without background thread
        ext = os.path.splitext(path)[1].lower()
        if ext in MediaViewer.VIDEO_EXTS:
            self.image_viewer.load_path(path)
            self.zoom_slider.setValue(100)  # Reset zoom for videos
            return

        # Handle images with background loading and caching
        pix = QPixmap()
        if QPixmapCache.find(path, pix):
            self.image_viewer.show_pixmap(pix)
            self.zoom_slider.setValue(self.image_viewer.zoom_pct)
            return

        self._preview_loader = PreviewLoader(path, self.image_viewer.size())
        self._preview_thread = QThread()
        self._preview_loader.moveToThread(self._preview_thread)
        self._preview_thread.started.connect(self._preview_loader.run, Qt.QueuedConnection)
        self._preview_loader.finished.connect(self._preview_thread.quit, Qt.QueuedConnection)
        self._preview_thread.finished.connect(self._preview_thread.deleteLater, Qt.QueuedConnection)
        self._preview_loader.finished.connect(self._preview_loader.deleteLater, Qt.QueuedConnection)
        self._preview_loader.finished.connect(self._on_preview_loaded, Qt.QueuedConnection)
        self._preview_thread.start()

    @Slot(str, QImage)
    def _on_preview_loaded(self, path: str, image: QImage) -> None:
        if self._preview_thread:
            self._preview_thread.wait()
            self._preview_thread = None
        self._preview_loader = None
        if image.isNull():
            logging.getLogger(__name__).warning("Failed to load preview: %s", path)
            placeholder = self.image_viewer.image_viewer.placeholder_pixmap
            self.image_viewer.show_pixmap(placeholder)
            self.zoom_slider.setValue(self.image_viewer.zoom_pct)
            return
        pixmap = QPixmap.fromImage(image)
        QPixmapCache.insert(path, pixmap)
        self.image_viewer.show_pixmap(pixmap)
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

    def clear_selected_suffixes(self):
        rows = [idx.row() for idx in self.table_widget.selectionModel().selectedRows()]
        self.table_widget.setSortingEnabled(False)
        for row in rows:
            item0 = self.table_widget.item(row, 1)
            if not item0:
                continue
            settings: ItemSettings = item0.data(ROLE_SETTINGS)
            if settings is None:
                settings = ItemSettings(item0.data(Qt.UserRole))
                item0.setData(ROLE_SETTINGS, settings)
            settings.suffix = ""
            cell = self.table_widget.item(row, 4)
            if cell:
                self._ignore_table_changes = True
                try:
                    cell.setText("")
                finally:
                    self._ignore_table_changes = False
                cell.setToolTip("")
            self.update_row_background(row, settings)
        self.table_widget.sync_check_column()
        self.on_table_selection_changed()

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
        dlg = CompressionDialog(
            paths,
            convert_heic,
            parent=self,
            state_manager=self.state_manager,
        )
        if dlg.exec() == QDialog.Accepted:
            for row, new_path, size_bytes, compressed_bytes in dlg.final_results:
                item0 = self.table_widget.item(row, 1)
                item0.setData(Qt.UserRole, new_path)
                item0.setText(os.path.basename(new_path))
                st: ItemSettings = item0.data(ROLE_SETTINGS)
                if st:
                    st.size_bytes = size_bytes
                    st.compressed_bytes = compressed_bytes

    def convert_selected_to_jpeg(self):
        rows = [idx.row() for idx in self.table_widget.selectionModel().selectedRows()]
        if not rows:
            return
        from ..logic.heic_converter import convert_to_jpeg
        total = len(rows)
        progress = QProgressDialog(
            "Converting to JPEG...",
            tr("abort"),
            0,
            total,
            self,
        )
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(200)
        progress.setValue(0)
        # store progress dialog and context for use in the completion slot
        self._convert_progress = progress
        self._convert_total = total

        def task(row):
            item0 = self.table_widget.item(row, 1)
            if not item0:
                return (row, None, None, None)
            path = item0.data(Qt.UserRole)
            new_path = convert_to_jpeg(path)
            size = os.path.getsize(new_path) if new_path != path else None
            return (row, path, new_path, size)

        # set up conversion worker and thread
        self._convert_worker = Worker(task, rows)
        self._convert_thread = QThread()
        self._convert_worker.moveToThread(self._convert_thread)
        # start conversion when thread starts
        self._convert_thread.started.connect(self._convert_worker.run, Qt.QueuedConnection)
        # update progress and handle cancellation
        self._convert_worker.progress.connect(
            lambda d, _t, _p: progress.setValue(d), Qt.QueuedConnection
        )
        progress.canceled.connect(self._convert_worker.stop, Qt.QueuedConnection)
        # store context for completion
        self._convert_total = total
        self._convert_progress = progress
        current = self.table_widget.currentRow()
        self._convert_current_row = current
        # connect finished signal to our slot and start the conversion thread
        self._convert_worker.finished.connect(self._on_convert_finished, Qt.QueuedConnection)
        self._convert_thread.start()

    @Slot(list)
    def _on_convert_finished(self, results: list):
        """Handle JPEG conversion completion in the GUI thread."""
        # close and delete the progress dialog
        progress = getattr(self, '_convert_progress', None)
        if progress:
            progress.close()
            progress.deleteLater()
            self._convert_progress = None
        total = getattr(self, '_convert_total', None)
        current = getattr(self, '_convert_current_row', None)
        # stop and delete the conversion thread
        if self._convert_thread:
            self._convert_thread.quit()
            self._convert_thread.wait()
            self._convert_thread.deleteLater()
        # delete the worker
        if self._convert_worker:
            self._convert_worker.deleteLater()
        # clear references
        self._convert_thread = None
        self._convert_worker = None
        # apply conversion results
        converted = 0
        for row, orig, new_path, size in results:
            if new_path and new_path != orig:
                item0 = self.table_widget.item(row, 1)
                item0.setData(Qt.UserRole, new_path)
                item0.setText(os.path.basename(new_path))
                if size is not None:
                    st: ItemSettings = item0.data(ROLE_SETTINGS)
                    if st:
                        st.size_bytes = size
                        st.compressed_bytes = size
                if row == current:
                    self.load_preview(new_path)
                converted += 1
        # show completion message
        QMessageBox.information(
            self,
            tr("done"),
            f"Converted {converted} of {total} images to JPEG."
        )

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
            elif self.rename_mode == MODE_POSITION:
                cell_pos = self.table_widget.item(row, 2)
                if cell_pos:
                    settings.position = cell_pos.text().strip()
            elif self.rename_mode == MODE_PA_MAT:
                cell_mat = self.table_widget.item(row, 2)
                if cell_mat:
                    settings.pa_mat = cell_mat.text().strip()
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
        if self.state_manager:
            w = self.state_manager.get("preview_width", 600)
            h = self.state_manager.get("preview_height", 400)
            dlg.resize(w, h)
        dlg_layout = QVBoxLayout(dlg)
        tbl = QTableWidget(len(table_mapping), 2, dlg)
        tbl.setHorizontalHeaderLabels([
            tr("current_name"),
            tr("proposed_new_name"),
        ])
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

        btns = QDialogButtonBox(parent=dlg)
        btn_all = btns.addButton(tr("rename_all"), QDialogButtonBox.AcceptRole)
        btn_sel = btns.addButton(tr("rename_selected"), QDialogButtonBox.AcceptRole)
        btn_cancel = btns.addButton(QDialogButtonBox.Cancel)
        dlg_layout.addWidget(btns)

        btn_cancel.clicked.connect(dlg.reject)
        btn_all.clicked.connect(lambda: (dlg.accept(), self.direct_rename()))
        btn_sel.clicked.connect(lambda: (dlg.accept(), self.direct_rename_selected()))

        dlg.exec()
        if self.state_manager:
            self.state_manager.set("preview_width", dlg.width())
            self.state_manager.set("preview_height", dlg.height())
            self.state_manager.save()

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
        compress = dlg.compress_after
        config_manager.set('compress_after_rename', compress)
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
        self.execute_rename_with_progress(table_mapping, compress=compress)

    def set_status_message(self, message: str | None) -> None:
        """Display an additional message in the status bar."""
        self.status_message = message or ""
        self.update_status()
    def execute_rename_with_progress(self, table_mapping, compress: bool = False):
        self.set_status_message(tr("renaming_files"))
        self.table_widget.setSortingEnabled(False)
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

        if compress:
            cfg = config_manager.load()
            compressor = ImageCompressor(
                max_size_kb=cfg.get("compression_max_size_kb", 2048),
                quality=cfg.get("compression_quality", 95),
                reduce_resolution=cfg.get("compression_reduce_resolution", True),
                resize_only=cfg.get("compression_resize_only", False),
                max_width=cfg.get("compression_max_width", 0) or None,
                max_height=cfg.get("compression_max_height", 0) or None,
            )
        else:
            compressor = None

        # perform rename synchronously to avoid thread issues
        results: list[dict] = []
        for idx, (row, orig, new_name, new_path) in enumerate(table_mapping, start=1):
            if progress.wasCanceled():
                break
            result = {
                "row": row,
                "orig": orig,
                "new": new_path,
                "old_size": None,
                "new_size": None,
                "error": None,
            }
            try:
                orig_abs = os.path.abspath(orig)
                new_abs = os.path.abspath(new_path)
                if orig_abs != new_abs:
                    os.rename(orig, new_path)
                final_path = new_path
                if compressor and os.path.splitext(new_path)[1].lower() not in MediaViewer.VIDEO_EXTS:
                    old_size = os.path.getsize(new_path)
                    final_path, new_size, _ = compressor.compress(new_path)
                    result["old_size"] = old_size
                    result["new_size"] = new_size
                result["new"] = final_path
            except Exception as e:
                result["error"] = str(e)
            results.append(result)
            progress.setValue(idx)
            QApplication.processEvents()

        # finalize rename operations
        progress.close()
        used_tags: list[str] = []
        done = len(results)
        total_local = total
        for res in results:
            if res.get("error"):
                QMessageBox.warning(
                    self,
                    tr("rename_failed"),
                    f"Error renaming:\n{res['orig']}\n→ {res['new']}\nError: {res['error']}"
                )
                continue
            row = res["row"]
            new_path = res["new"]
            item0 = self.table_widget.item(row, 1)
            if item0:
                item0.setText(os.path.basename(new_path))
                item0.setData(Qt.UserRole, new_path)
                settings = item0.data(ROLE_SETTINGS)
                if settings and self.rename_mode == MODE_NORMAL:
                    used_tags.extend(settings.tags)
                self.undo_manager.record(row, res["orig"], new_path)
                if compressor and os.path.splitext(new_path)[1].lower() not in MediaViewer.VIDEO_EXTS:
                    if settings:
                        settings.size_bytes = res.get("old_size")
                        settings.compressed_bytes = res.get("new_size")

        if progress.wasCanceled():
            QMessageBox.information(
                self,
                tr("partial_rename"),
                tr("partial_rename_msg").format(done=done, total=total_local)
            )
        else:
            QMessageBox.information(self, tr("done"), tr("rename_done"))
            if used_tags and self.rename_mode == MODE_NORMAL:
                increment_tags(used_tags)
                self.tag_panel.rebuild()
        self.set_status_message(None)
        self._enable_sorting()

    def update_status(self) -> None:
        """Refresh the selection count and optional message."""
        selected = len(self.table_widget.selectionModel().selectedRows())
        total = self.table_widget.rowCount()
        text = tr("status_selected").format(current=selected, total=total)
        if self.status_message:
            text = f"{text} - {self.status_message}"
        self.lbl_status.setText(text)

    def _enable_sorting(self) -> None:
        header = self.table_widget.horizontalHeader()
        self.table_widget.setSortingEnabled(True)
        self.table_widget.sortByColumn(
            header.sortIndicatorSection(),
            header.sortIndicatorOrder(),
        )

    def closeEvent(self, event):
        # stop selection change timer
        try:
            self._sel_change_timer.stop()
        except Exception:
            pass
        # ensure any playing video is stopped to release multimedia resources
        self.image_viewer.video_player.player.stop()
        if self._preview_loader:
            self._preview_loader.stop()
        if self._preview_thread:
            if self._preview_thread.isRunning():
                self._preview_thread.quit()
                self._preview_thread.wait()
            if self._preview_loader:
                self._preview_loader.deleteLater()
                self._preview_loader = None
            self._preview_thread = None
        # ensure any running conversion threads are stopped
        if getattr(self, '_convert_thread', None) and self._convert_thread.isRunning():
            if getattr(self, '_convert_worker', None):
                self._convert_worker.stop()
            self._convert_thread.quit()
            self._convert_thread.wait()
            self._convert_thread = None
            self._convert_worker = None
        if self._rename_thread and self._rename_thread.isRunning():
            if self._rename_worker:
                self._rename_worker.stop()
            self._rename_thread.quit()
            # wait indefinitely for the rename thread to finish
            self._rename_thread.wait()
            self._rename_thread = None
            self._rename_worker = None
        if self.state_manager:
            self.state_manager.set("width", self.width())
            self.state_manager.set("height", self.height())
            self.state_manager.set("splitter_sizes", self.splitter.sizes())
            self.state_manager.save()
        super().closeEvent(event)

