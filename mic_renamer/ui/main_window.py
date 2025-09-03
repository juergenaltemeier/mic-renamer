import logging
import json
import re
import os
from datetime import datetime
from pathlib import Path

import gc
from PySide6.QtCore import (QItemSelectionModel, QPoint, QSize, Qt, Signal, Slot, QThread, QTimer)
from PySide6.QtGui import QImage, QPixmap, QPixmapCache, QAction, QImageReader
from PySide6.QtWidgets import (QApplication, QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QSizePolicy, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QProgressDialog, QToolBar, QMenu, QToolButton, QSplitter, QComboBox, QDialogButtonBox, QInputDialog)

from .. import config_manager
from ..logic.image_compressor import ImageCompressor
from ..logic.renamer import Renamer
from ..logic.settings import ItemSettings
from ..logic.tag_usage import increment_tags
from ..logic.undo_manager import UndoManager
from ..utils.i18n import set_language, tr
from ..utils.workers import PreviewLoader
from .constants import DEFAULT_MARGIN, DEFAULT_SPACING
from .dialogs.help_dialog import HelpDialog
from .otp_input import OtpInput
from .panels import MediaViewer, ModeTabs, TagPanel
from .rename_options_dialog import RenameOptionsDialog
from .settings_dialog import SettingsDialog
from .theme import resource_icon



def _validate_and_format_date(date_str: str) -> str:
    """Validate and format date input to YYMMDD format."""
    if not date_str:
        return ""
    
    # Remove any non-digit characters
    digits_only = re.sub(r'\D', '', date_str)
    
    # If it's already in YYMMDD format (6 digits), validate and return
    if len(digits_only) == 6:
        try:
            year = int(digits_only[:2]) + 2000  # Convert YY to YYYY
            month = int(digits_only[2:4])
            day = int(digits_only[4:6])
            datetime(year, month, day)  # Validate date
            return digits_only
        except ValueError:
            pass
    
    # Try to parse various date formats
    date_formats = [
        '%Y-%m-%d',    # 2024-12-26
        '%Y/%m/%d',    # 2024/12/26
        '%d-%m-%Y',    # 26-12-2024
        '%d/%m/%Y',    # 26/12/2024
        '%m-%d-%Y',    # 12-26-2024
        '%m/%d/%Y',    # 12/26/2024
        '%d-%m-%y',    # 26-12-24
        '%d/%m/%y',    # 26/12/24
        '%m-%d-%y',    # 12-26-24
        '%m/%d/%y',    # 12/26/24
        '%Y%m%d',      # 20241226
    ]
    
    for fmt in date_formats:
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            return parsed_date.strftime('%y%m%d')
        except ValueError:
            continue
    
    # If no format matches, try with digits_only if it has enough digits
    if len(digits_only) == 8:  # YYYYMMDD
        try:
            year = int(digits_only[:4])
            month = int(digits_only[4:6])
            day = int(digits_only[6:8])
            parsed_date = datetime(year, month, day)
            return parsed_date.strftime('%y%m%d')
        except ValueError:
            pass
    
    # Return original if we can't parse it
    return date_str



ROLE_SETTINGS = int(Qt.ItemDataRole.UserRole) + 1
MODE_NORMAL = "normal"
MODE_POSITION = "position"
MODE_PA_MAT = "pa_mat"

class RenamerApp(QWidget):
    """
    The main window of the Mic-Renamer application.

    This class orchestrates the entire user interface, including the toolbar,
    media preview, file list, and tag panel. It handles user interactions,
    manages application state, and coordinates with the backend logic for
    renaming, compression, and other operations.
    """

    def __init__(self, state_manager=None):
        """
        Initializes the main application window.

        Args:
            state_manager: An optional instance of the StateManager for
                           persisting application state.
        """
        super().__init__()
        self.logger = logging.getLogger(__name__)
        set_language(config_manager.get("language", "en"))
        self.state_manager = state_manager
        self.undo_manager = UndoManager()
        self.rename_mode = MODE_NORMAL
        self._preview_thread: QThread | None = None
        self._rename_thread = None
        self._preview_loader: PreviewLoader | None = None
        self._session_recording_started = False
        self.status_message = "" # Initialize status_message here
        self.setWindowTitle(tr("app_title"))

        self._setup_ui()
        self._connect_signals()
        self._load_initial_state()
        self._setup_shortcuts()
        # Track last requested preview path to ignore stale worker results
        self._last_preview_path: str | None = None
        # Hold a single pending preview path if a load is already in progress
        self._pending_preview_path: str | None = None
        # Create a persistent preview worker thread and loader
        try:
            self._preview_thread = QThread(self)
            self._preview_loader = PreviewLoader("", self.size())
            self._preview_loader.moveToThread(self._preview_thread)
            self._preview_loader.finished.connect(self._on_preview_loaded)
            self._preview_thread.start()
            self._is_preview_loading = False
        except Exception as e:
            self.logger.error(f"Failed to initialize preview worker thread: {e}")
            self._preview_thread = None
            self._preview_loader = None
            self._is_preview_loading = False

    def _check_and_offer_certificate_install(self):
        pass

    def _setup_ui(self):
        """Creates and arranges all UI components."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(
            DEFAULT_MARGIN, DEFAULT_MARGIN, DEFAULT_MARGIN, DEFAULT_MARGIN
        )
        main_layout.setSpacing(DEFAULT_SPACING)

        self._setup_toolbar()
        main_layout.addWidget(self.toolbar)

        self._setup_main_splitter()
        self._setup_tag_panel()

        self.tag_splitter = QSplitter(Qt.Vertical)
        self.tag_splitter.addWidget(self.splitter)
        self.tag_splitter.addWidget(self.tag_container)
        main_layout.addWidget(self.tag_splitter, 1)

        self._setup_status_bar()
        main_layout.addLayout(self.status_layout)

    def _setup_toolbar(self):
        """Configures the main application toolbar."""
        self.toolbar = QToolBar()
        self.toolbar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.toolbar.setIconSize(QSize(20, 20))
        self.setup_toolbar()  # This method is defined below and populates the toolbar

        self.btn_toggle_tags = QToolButton()
        self.btn_toggle_tags.setIcon(resource_icon("eye.svg"))
        self.btn_toggle_tags.setText(tr("show_tags"))
        self.btn_toggle_tags.setCheckable(True)
        self.btn_toggle_tags.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toolbar.addWidget(self.btn_toggle_tags)

    def _setup_main_splitter(self):
        """Sets up the main horizontal splitter for viewer and table."""
        self.splitter = QSplitter(Qt.Horizontal)
        viewer_widget = self._create_viewer_widget()
        table_container = self._create_table_container()
        self.splitter.addWidget(viewer_widget)
        self.splitter.addWidget(table_container)

    def _create_viewer_widget(self) -> QWidget:
        """Creates the widget for displaying media (image/video) previews."""
        viewer_widget = QWidget()
        viewer_layout = QVBoxLayout(viewer_widget)
        viewer_layout.setContentsMargins(0, 0, 0, 0)
        viewer_layout.setSpacing(0)

        self.media_viewer = MediaViewer() # Assign MediaViewer instance to self.media_viewer
        viewer_layout.addWidget(self.media_viewer)

        viewer_toolbar = QToolBar()
        viewer_toolbar.setIconSize(QSize(20, 20))
        viewer_layout.addWidget(viewer_toolbar)

        self.viewer_actions = []
        self.viewer_buttons = []

        icon_size = QSize(20, 20)

        actions = {
            "zoom_fit": (resource_icon("zoom-fit.svg"), "Fit", self.media_viewer.zoom_fit),
            "prev": (resource_icon("prev.svg"), "Prev", self.goto_previous_item),
            "next": (resource_icon("next.svg"), "Next", self.goto_next_item),
            "rot_left": (resource_icon("rotate-left.svg"), "Rotate Left", self.media_viewer.rotate_left),
            "rot_right": (resource_icon("rotate-right.svg"), "Rotate Right", self.media_viewer.rotate_right),
        }

        for name, (icon, text, slot) in actions.items():
            action = QAction(icon, text, self)
            action.triggered.connect(slot)
            button = QToolButton()
            button.setDefaultAction(action)
            button.setIconSize(icon_size)
            viewer_toolbar.addWidget(button)
            self.viewer_actions.append(action)
            self.viewer_buttons.append(button)

        return viewer_widget

    def _create_viewer_toolbar(self) -> QHBoxLayout:
        """Creates the toolbar for the media viewer."""
        self.viewer_actions: list[QAction] = []
        self.viewer_buttons: list[QToolButton] = []
        viewer_toolbar = QHBoxLayout()
        icon_size = QSize(20, 20)

        actions = {
            "zoom_fit": (resource_icon("zoom-fit.svg"), "Fit", self.media_viewer.zoom_fit),
            "prev": (resource_icon("prev.svg"), "Prev", self.goto_previous_item),
            "next": (resource_icon("next.svg"), "Next", self.goto_next_item),
            "rot_left": (resource_icon("rotate-left.svg"), "Rotate Left", self.media_viewer.rotate_left),
            "rot_right": (resource_icon("rotate-right.svg"), "Rotate Right", self.media_viewer.rotate_right),
        }

        for name, (icon, text, slot) in actions.items():
            action = QAction(icon, text, self)
            action.triggered.connect(slot)
            button = QToolButton()
            button.setDefaultAction(action)
            button.setIconSize(icon_size)
            viewer_toolbar.addWidget(button)
            self.viewer_actions.append(action)
            self.viewer_buttons.append(button)

        return viewer_toolbar

    def _create_table_container(self) -> QWidget:
        """Creates the widget containing the mode tabs and file table."""
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(
            DEFAULT_MARGIN, DEFAULT_MARGIN, DEFAULT_MARGIN, DEFAULT_MARGIN
        )
        table_layout.setSpacing(DEFAULT_SPACING)

        self.mode_tabs = ModeTabs()
        self.combo_mode = QComboBox()
        self.combo_mode.addItem(tr("mode_normal"), MODE_NORMAL)
        self.combo_mode.addItem(tr("mode_position"), MODE_POSITION)
        self.combo_mode.addItem(tr("mode_pa_mat"), MODE_PA_MAT)
        self.toolbar.addWidget(self.combo_mode)

        self.table_widget: QTableWidget = self.mode_tabs.current_table()
        table_layout.addWidget(self.mode_tabs)
        return table_container

    def _setup_tag_panel(self):
        """Sets up the tag panel and its container."""
        self.tag_panel = TagPanel()
        self.tag_container = QWidget()
        tag_container_layout = QVBoxLayout(self.tag_container)
        tag_container_layout.setContentsMargins(0, 0, 0, 0)
        tag_container_layout.setSpacing(0)
        tag_container_layout.addWidget(self.tag_panel)

    def _setup_status_bar(self):
        """Sets up the status bar at the bottom of the window."""
        self.status_layout = QHBoxLayout()
        self.lbl_status = QLabel()
        self.lbl_status.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.lbl_status.setMaximumHeight(
            self.lbl_status.fontMetrics().height() + 4
        )
        self.status_layout.addWidget(self.lbl_status)

        self.lbl_session_status = QLabel()
        self.lbl_session_status.setFixedSize(16, 16)
        self.status_layout.addWidget(self.lbl_session_status)

    def _connect_signals(self):
        """Connects all signals to their corresponding slots."""
        self.btn_toggle_tags.clicked.connect(self.toggle_tag_panel)
        self.combo_mode.currentIndexChanged.connect(self.mode_tabs.tabs.setCurrentIndex)
        self.mode_tabs.tabs.currentChanged.connect(self.on_tab_changed)

        self._ignore_table_changes = False
        for table in self.mode_tabs.all_tables():
            table.itemChanged.connect(self.on_table_item_changed)
            table.pathsAdded.connect(self.update_status)
            table.pathsAdded.connect(self._on_paths_added)
            table.remove_selected_requested.connect(self.remove_selected_items)
            table.delete_selected_requested.connect(self.delete_selected_files)
            table.clear_suffix_requested.connect(self.clear_selected_suffixes)
            table.append_suffix_requested.connect(self.add_suffix_for_selected)
            table.clear_list_requested.connect(self.clear_all)
            table.itemSelectionChanged.connect(self.on_table_selection_changed)

        self.tag_panel.tagToggled.connect(self.on_tag_toggled)
        self.tag_panel.arrowKeyPressed.connect(self.on_tag_panel_arrow_key)
        self.tag_splitter.splitterMoved.connect(self._on_tag_splitter_moved)

        self._sel_change_timer = QTimer(self)
        self._sel_change_timer.setSingleShot(True)
        self._sel_change_timer.setInterval(180)
        self._sel_change_timer.timeout.connect(self._apply_selection_change)

        self._session_save_timer = QTimer(self)
        self._session_save_timer.setSingleShot(True)
        self._session_save_timer.setInterval(2000)  # 2 seconds
        self._session_save_timer.timeout.connect(self.save_session)

        self.table_widget.itemChanged.connect(self.on_change_made)
        self.input_project.textChanged.connect(self.on_change_made)

    def _load_initial_state(self):
        """Loads and applies the initial state of the application."""
        if self.state_manager:
            sizes = self.state_manager.get("splitter_sizes")
            if sizes:
                self.splitter.setSizes(sizes)

        sizes = config_manager.get("tag_panel_splitter_sizes", None)
        if sizes:
            try:
                self.tag_splitter.setSizes(sizes)
            except Exception as e:
                self.logger.warning(f"Could not set tag splitter sizes: {e}")

        visible = config_manager.get("tag_panel_visible", False)
        self.tag_container.setVisible(visible)
        self.btn_toggle_tags.setChecked(visible)
        self.btn_toggle_tags.setToolTip(tr("hide_tags") if visible else tr("show_tags"))
        self.btn_toggle_tags.setText(tr("hide_tags") if visible else tr("show_tags"))

        self.set_item_controls_enabled(False)
        self.status_message = ""
        self.update_status()
        self.apply_toolbar_style(config_manager.get("toolbar_style", "icons"))

        self.set_session_status(True)
        self.check_for_crashed_session()


    def _setup_shortcuts(self):
        find_action = QAction(self)
        find_action.setShortcut(Qt.CTRL | Qt.Key_F)
        find_action.triggered.connect(self.focus_tag_search)
        self.addAction(find_action)

    def focus_tag_search(self):
        self.tag_panel.search_bar.setFocus()
        self.tag_panel.search_bar.selectAll()

    def on_tag_panel_arrow_key(self, key):
        if key == Qt.Key_Up:
            self.goto_previous_item()
        elif key == Qt.Key_Down:
            self.goto_next_item()

    def on_change_made(self):
        if not self._session_recording_started:
            return
        self.set_session_status(False)
        self._session_save_timer.start()

    def set_session_status(self, saved: bool):
        if saved:
            self.lbl_session_status.setPixmap(resource_icon("status-blue.svg").pixmap(16, 16))
            self.lbl_session_status.setToolTip(tr("session_saved"))
        else:
            self.lbl_session_status.setPixmap(resource_icon("status-inactive.svg").pixmap(16, 16))
            self.lbl_session_status.setToolTip(tr("session_not_saved"))

    def set_splitter_sizes(self, sizes: list[int] | None) -> None:
        """Set the splitter sizes if a valid list is provided."""
        if sizes:
            self.splitter.setSizes(sizes)

    def toggle_tag_panel(self, checked: bool):
        # Show/hide the tag panel container in the splitter
        self.tag_container.setVisible(checked)
        self.btn_toggle_tags.setToolTip(tr("hide_tags") if checked else tr("show_tags"))
        config_manager.set("tag_panel_visible", checked)
    
    def _on_tag_splitter_moved(self, pos: int, index: int) -> None:
        """Save vertical splitter sizes when user resizes tag panel."""
        try:
            sizes = self.tag_splitter.sizes()
            config_manager.set("tag_panel_splitter_sizes", sizes)
        except Exception:
            pass

    def rebuild_tag_checkboxes(self):
        self.tag_panel.rebuild()

    def setup_toolbar(self):
        tb = self.toolbar
        # unify spacing between toolbar items
        lt = tb.layout()
        if lt:
            lt.setSpacing(6)
        self.toolbar_actions = []
        self.toolbar_action_icons = []
        self.menu_actions = []

        # actions collected in the "Add" menu
        icon_add_files = resource_icon("file-plus.svg")
        act_add_files = QAction(icon_add_files, tr("add_files"), self)
        act_add_files.setToolTip(tr("tip_add_files"))
        act_add_files.triggered.connect(self.add_files_dialog)
        self.menu_actions.append(act_add_files)

        icon_add_folder = resource_icon("folder-plus.svg")
        act_add_folder = QAction(icon_add_folder, tr("add_folder"), self)
        act_add_folder.setToolTip(tr("tip_add_folder"))
        act_add_folder.triggered.connect(self.add_folder_dialog)
        self.menu_actions.append(act_add_folder)

        act_add_folder_recursive = QAction(icon_add_folder, tr("add_folder_recursive"), self)
        act_add_folder_recursive.setToolTip(tr("tip_add_folder_recursive"))
        act_add_folder_recursive.triggered.connect(self.add_folder_with_subdirectories)
        self.menu_actions.append(act_add_folder_recursive)

        act_add_untagged = QAction(icon_add_folder, tr("add_untagged_folder"), self)
        act_add_untagged.setToolTip(tr("tip_add_untagged_folder"))
        act_add_untagged.triggered.connect(self.add_untagged_from_folder)
        self.menu_actions.append(act_add_untagged)

        act_add_untagged_recursive = QAction(icon_add_folder, tr("add_untagged_folder_recursive"), self)
        act_add_untagged_recursive.setToolTip(tr("tip_add_untagged_folder_recursive"))
        act_add_untagged_recursive.triggered.connect(self.add_untagged_from_folder_recursive)
        self.menu_actions.append(act_add_untagged_recursive)

        # create drop-down menu button for adding items
        self.menu_add = QMenu(tr("add_menu"), self)
        self.menu_add.addAction(act_add_files)
        self.menu_add.addAction(act_add_folder)
        self.menu_add.addAction(act_add_folder_recursive)
        self.menu_add.addSeparator()
        self.menu_add.addAction(act_add_untagged)
        self.menu_add.addAction(act_add_untagged_recursive)
        self.menu_add.addSeparator()
        act_set_import_dir = QAction(tr("set_import_directory"), self)
        act_set_import_dir.triggered.connect(self.set_import_directory)
        self.menu_add.addAction(act_set_import_dir)
        self.menu_actions.append(act_set_import_dir)

        self.icon_add_menu = resource_icon("file-plus.svg")
        self.btn_add_menu = QToolButton()
        self.btn_add_menu.setIconSize(self.toolbar.iconSize())
        self.btn_add_menu.setMenu(self.menu_add)
        self.btn_add_menu.setIcon(self.icon_add_menu)
        self.btn_add_menu.setText(tr("add_menu"))
        self.btn_add_menu.setToolTip(tr("tip_add_menu"))
        self.btn_add_menu.setPopupMode(QToolButton.InstantPopup)
        tb.addWidget(self.btn_add_menu)

        tb.addSeparator()

        # Edit menu
        self.menu_edit = QMenu(tr("edit_menu"), self)
        self.menu_edit_actions = []
        
        icon_compress = resource_icon("arrow-down-circle.svg")
        act_compress = QAction(icon_compress, tr("compress"), self)
        act_compress.setToolTip(tr("tip_compress"))
        act_compress.triggered.connect(self.compress_selected)
        self.menu_edit.addAction(act_compress)
        self.menu_edit_actions.append(act_compress)

        icon_convert = resource_icon("image.svg")
        act_convert = QAction(icon_convert, tr("convert_heic"), self)
        act_convert.setToolTip(tr("tip_convert_heic"))
        act_convert.triggered.connect(self.convert_selected_to_jpeg)
        self.menu_edit.addAction(act_convert)
        self.menu_edit_actions.append(act_convert)

        self.menu_edit.addSeparator()

        icon_undo = resource_icon("rotate-ccw.svg")
        act_undo = QAction(icon_undo, tr("undo_rename"), self)
        act_undo.setToolTip(tr("tip_undo_rename"))
        act_undo.triggered.connect(self.undo_rename)
        self.menu_edit.addAction(act_undo)
        self.menu_edit_actions.append(act_undo)

        self.menu_edit.addSeparator()

        icon_remove_sel = resource_icon("trash-2.svg")
        self.act_remove_sel = QAction(icon_remove_sel, tr("remove_selected"), self)
        self.act_remove_sel.setToolTip(tr("tip_remove_selected"))
        self.act_remove_sel.triggered.connect(self.remove_selected_items)
        self.menu_edit.addAction(self.act_remove_sel)
        self.menu_edit_actions.append(self.act_remove_sel)
        # delete selected files from disk
        icon_delete_sel = resource_icon("trash-2.svg")
        act_delete_sel = QAction(icon_delete_sel, tr("delete_selected_files"), self)
        act_delete_sel.setToolTip(tr("tip_delete_selected_files"))
        act_delete_sel.triggered.connect(self.delete_selected_files)
        self.menu_edit.addAction(act_delete_sel)
        self.menu_edit_actions.append(act_delete_sel)

        icon_clear_suffix = resource_icon("suffix-clear.svg")
        self.act_clear_suffix = QAction(icon_clear_suffix, tr("clear_suffix"), self)
        self.act_clear_suffix.setToolTip(tr("tip_clear_suffix"))
        self.act_clear_suffix.triggered.connect(self.clear_selected_suffixes)
        self.menu_edit.addAction(self.act_clear_suffix)
        self.menu_edit_actions.append(self.act_clear_suffix)

        icon_clear = resource_icon("clear.svg")
        self.act_clear = QAction(icon_clear, tr("clear_list"), self)
        self.act_clear.setToolTip(tr("tip_clear_list"))
        self.act_clear.triggered.connect(self.clear_all)
        self.menu_edit.addAction(self.act_clear)
        self.menu_edit_actions.append(self.act_clear)
        
        icon_restore_session = resource_icon("history-blue.svg")
        act_restore_session = QAction(icon_restore_session, tr("restore_session"), self)
        act_restore_session.setToolTip(tr("tip_restore_session"))
        act_restore_session.triggered.connect(self.restore_session)
        self.menu_edit.addAction(act_restore_session)
        self.menu_edit_actions.append(act_restore_session)

        self.icon_edit_menu = resource_icon("edit-blue.svg")
        self.btn_edit_menu = QToolButton()
        self.btn_edit_menu.setIconSize(self.toolbar.iconSize())
        self.btn_edit_menu.setMenu(self.menu_edit)
        self.btn_edit_menu.setIcon(self.icon_edit_menu)
        self.btn_edit_menu.setText(tr("edit_menu"))
        self.btn_edit_menu.setToolTip(tr("edit_menu"))
        self.btn_edit_menu.setPopupMode(QToolButton.InstantPopup)
        tb.addWidget(self.btn_edit_menu)

        tb.addSeparator()

        icon_preview = resource_icon("eye.svg")
        act_preview = QAction(icon_preview, tr("preview_rename"), self)
        act_preview.setToolTip(tr("tip_preview_rename"))
        act_preview.triggered.connect(self.preview_rename)
        self.toolbar_actions.append(act_preview)
        self.toolbar_action_icons.append(icon_preview)

        icon_settings = resource_icon("settings.svg")
        act_settings = QAction(icon_settings, tr("settings_title"), self)
        act_settings.setToolTip(tr("tip_settings"))
        act_settings.triggered.connect(self.open_settings)
        self.toolbar_actions.append(act_settings)
        self.toolbar_action_icons.append(icon_settings)

        tb.addActions(self.toolbar_actions)

        # help button
        self.act_help = QAction(resource_icon("help-blue.svg"), tr("help_title"), self)
        self.act_help.setToolTip(tr("tip_help"))
        self.act_help.triggered.connect(self.show_help)
        tb.addAction(self.act_help)
        # insert fixed gap before project code input
        spacer = QWidget(self)
        spacer.setFixedWidth(12)
        spacer.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        tb.addWidget(spacer)
        # project code input
        self.input_project = OtpInput()
        self.input_project.setText(config_manager.get("last_project_number", ""))
        self.input_project.textChanged.connect(self.save_last_project_number)
        tb.addWidget(self.input_project)
        # alias for tests
        self.project_input = self.input_project

        


    def on_tab_changed(self, index):
        self.table_widget = self.mode_tabs.current_table()
        self.rename_mode = self.table_widget.mode

        is_position_mode = self.rename_mode == MODE_POSITION
        is_pa_mat_mode = self.rename_mode == MODE_PA_MAT

        self.table_widget.setColumnHidden(2, is_position_mode or is_pa_mat_mode)
        self.table_widget.setColumnHidden(3, is_position_mode)

        self.on_table_selection_changed()

    def open_settings(self):
        dlg = SettingsDialog(self, state_manager=self.state_manager)
        if dlg.exec() == QDialog.Accepted:
            cfg = config_manager.load()
            language = cfg.get("language", "en")
            set_language(language)
            
            # Re-apply theme
            from .theme import apply_styles
            theme = cfg.get("theme", "dark")
            apply_styles(QApplication.instance(), theme)
            
            self.update_translations(language=language)
            style = cfg.get("toolbar_style", "icons")
            self.apply_toolbar_style(style)

    def show_help(self):
        dlg = HelpDialog(self)
        dlg.exec()

    def save_last_project_number(self, text: str) -> None:
        config_manager.set("last_project_number", text.strip())
        self._session_save_timer.start()

    def update_translations(self, language: str | None = None):
        self.setWindowTitle(tr("app_title"))
        
        # Update main toolbar actions
        actions = self.toolbar_actions
        labels = [
            "preview_rename", "settings_title"
        ]
        tips = [
            "tip_preview_rename", "tip_settings"
        ]
        for action, key, tip in zip(actions, labels, tips):
            action.setText(tr(key))
            action.setToolTip(tr(tip))

        if hasattr(self, "act_help"):
            self.act_help.setText(tr("help_title"))
            self.act_help.setToolTip(tr("tip_help"))

        # Update "Add" menu actions
        menu_actions = self.menu_actions
        menu_labels = [
            "add_files", "add_folder", "add_folder_recursive", "add_untagged_folder", "add_untagged_folder_recursive", "set_import_directory"
        ]
        menu_tips = [
            "tip_add_files", "tip_add_folder", "tip_add_folder_recursive", "tip_add_untagged_folder", "tip_add_untagged_folder_recursive", "tip_set_import_directory"
        ]
        for action, key, tip in zip(menu_actions, menu_labels, menu_tips):
            action.setText(tr(key))
            action.setToolTip(tr(tip))

        # update add menu title and button
        if hasattr(self, "menu_add"):
            self.menu_add.setTitle(tr("add_menu"))
        if hasattr(self, "btn_add_menu"):
            self.btn_add_menu.setText(tr("add_menu"))
            self.btn_add_menu.setToolTip(tr("tip_add_menu"))
            
        # Update "Edit" menu
        if hasattr(self, "menu_edit"):
            self.menu_edit.setTitle(tr("edit_menu"))
        if hasattr(self, "btn_edit_menu"):
            self.btn_edit_menu.setText(tr("edit_menu"))
            self.btn_edit_menu.setToolTip(tr("edit_menu"))

        if hasattr(self, "menu_edit_actions"):
            menu_edit_actions = self.menu_edit_actions
            menu_edit_labels = [
                "compress", "convert_heic", "undo_rename", "remove_selected", "delete_selected_files", "clear_suffix", "clear_list", "restore_session"
            ]
            menu_edit_tips = [
                "tip_compress", "tip_convert_heic", "tip_undo_rename", "tip_remove_selected", "tip_delete_selected_files", "tip_clear_suffix", "tip_clear_list", "tip_restore_session"
            ]
            for action, key, tip in zip(menu_edit_actions, menu_edit_labels, menu_edit_tips):
                action.setText(tr(key))
                action.setToolTip(tr(tip))
                
        # update show/hide tags toggle
        if hasattr(self, "btn_toggle_tags"):
            visible = self.tag_panel.isVisible()
            self.btn_toggle_tags.setToolTip(tr("hide_tags") if visible else tr("show_tags"))
            self.btn_toggle_tags.setText(tr("hide_tags") if visible else tr("show_tags"))
        self.mode_tabs.tabs.setTabText(0, tr("mode_normal"))
        self.mode_tabs.tabs.setTabText(1, tr("mode_position"))
        self.mode_tabs.tabs.setTabText(2, tr("mode_pa_mat"))
        if hasattr(self, "tag_panel"):
            self.tag_panel.retranslate_ui(language)
        self.update_status()

    def apply_toolbar_style(self, style: str) -> None:
        if style == "text":
            self.toolbar.setToolButtonStyle(Qt.ToolButtonTextOnly)
            if hasattr(self, "btn_add_menu"):
                self.btn_add_menu.setToolButtonStyle(Qt.ToolButtonTextOnly)
            if hasattr(self, "btn_edit_menu"):
                self.btn_edit_menu.setToolButtonStyle(Qt.ToolButtonTextOnly)
        else:
            self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            if hasattr(self, "btn_add_menu"):
                self.btn_add_menu.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            if hasattr(self, "btn_edit_menu"):
                self.btn_edit_menu.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

    def set_import_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            tr("set_import_directory"),
            config_manager.get('default_import_directory', '')
        )
        if directory:
            config_manager.set('default_import_directory', directory)

    def add_files_dialog(self):
        exts = " ".join(f"*{e}" for e in ItemSettings.ACCEPT_EXTENSIONS)
        filter_str = f"Images and Videos ({exts})"
        import_dir = config_manager.get('default_import_directory', '')
        files, _ = QFileDialog.getOpenFileNames(
            self, tr("add_files"), import_dir,
            filter_str
        )
        if files:
            self._import_paths(files)

    def add_folder_dialog(self):
        """Opens a dialog to select a folder and adds its contents to the list."""
        folder_path = self._get_import_directory(tr("add_folder"))
        if not folder_path:
            return

        try:
            paths = [
                str(p)
                for p in folder_path.iterdir()
                if p.is_file() and p.suffix.lower() in ItemSettings.ACCEPT_EXTENSIONS
            ]
            if paths:
                self._import_paths(paths)
            else:
                QMessageBox.information(self, tr("no_files_found"), tr("no_files_found_in_folder"))
        except OSError as e:
            self.logger.error(f"Error reading folder {folder_path}: {e}")
            QMessageBox.warning(self, tr("error"), tr("error_reading_folder").format(folder=folder_path, error=e))

    def add_folder_with_subdirectories(self):
        """Opens a dialog to select a folder and adds its contents recursively."""
        folder_path = self._get_import_directory(tr("add_folder_recursive"))
        if not folder_path:
            return

        try:
            paths = [
                str(p)
                for p in folder_path.rglob("*")
                if p.is_file() and p.suffix.lower() in ItemSettings.ACCEPT_EXTENSIONS
            ]
            if paths:
                self._import_paths(paths)
            else:
                QMessageBox.information(self, tr("no_files_found"), tr("no_files_found_in_folder"))
        except OSError as e:
            self.logger.error(f"Error reading folder {folder_path}: {e}")
            QMessageBox.warning(self, tr("error"), tr("error_reading_folder").format(folder=folder_path, error=e))

    def add_untagged_from_folder(self):
        self._add_untagged_files(recursive=False)

    def add_untagged_from_folder_recursive(self):
        self._add_untagged_files(recursive=True)

    def _get_import_directory(self, title: str) -> Path | None:
        """Opens a dialog to select a directory and returns it as a Path object."""
        directory = QFileDialog.getExistingDirectory(
            self,
            title,
            config_manager.get('default_import_directory', '')
        )
        if directory:
            return Path(directory)
        return None

    def _add_untagged_files(self, recursive: bool):
        """Adds files from a selected folder that do not contain any known tags."""
        folder_path = self._get_import_directory(tr("add_folder"))
        if not folder_path:
            return

        try:
            all_tags = set(self.tag_panel.tags_info.keys())
            paths = []
            file_iterator = folder_path.rglob("*") if recursive else folder_path.iterdir()

            for p in file_iterator:
                if p.is_file() and self._is_untagged_file(p.name, all_tags):
                    paths.append(str(p))

            if paths:
                self._import_paths(paths)
            else:
                QMessageBox.information(self, tr("no_untagged_files_found"), tr("no_untagged_files_found_in_folder"))
        except OSError as e:
            self.logger.error(f"Error reading folder {folder_path}: {e}")
            QMessageBox.warning(self, tr("error"), tr("error_reading_folder").format(folder=folder_path, error=e))

    def _is_untagged_file(self, filename: str, all_tags: set[str]) -> bool:
        """Checks if a filename contains any of the known tags."""
        p = Path(filename)
        base = p.stem
        ext = p.suffix.lower()

        if ext not in ItemSettings.ACCEPT_EXTENSIONS:
            return False

        parts = base.split('_')
        return not any(part in all_tags for part in parts)

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
            # Normalize the path to use forward slashes for consistency
            normalized_path = path.replace("\\", "/")
            # Import into all mode tabs
            self.mode_tabs.current_table().add_paths([normalized_path])
            progress.setValue(idx)
            QApplication.processEvents()
        progress.close()
        self._session_recording_started = True
        self._session_save_timer.start()

    def on_table_selection_changed(self):
        """Start or restart the selection change timer."""
        self._sel_change_timer.start()

    def _apply_selection_change(self):
        self.logger.debug("Applying selection change.")
        
        # Use the current row for the preview to ensure it follows focus
        current_row = self.table_widget.currentRow()
        if current_row < 0:
            # If no row is current (e.g., selection cleared), stop preview
            if self._preview_loader:
                self.logger.debug("Stopping previous preview loader due to no current row.")
                self._preview_loader.stop()
            self.media_viewer.load_path("")
            self.set_item_controls_enabled(False)
            (self.table_widget).sync_check_column()
            self.update_status()
            return

        rows = [idx.row() for idx in (self.table_widget).selectionModel().selectedRows()]
        if not rows:
            self.set_item_controls_enabled(False)
            (self.table_widget).sync_check_column()
            self.update_status()
            return

        self.set_item_controls_enabled(True)
        
        # Update tag panel based on the entire selection
        settings_list = []
        for r in rows:
            item0 = (self.table_widget).item(r, 1)
            if item0:
                st: ItemSettings = item0.data(ROLE_SETTINGS)
                if st:
                    settings_list.append(st)

        if self.rename_mode == MODE_NORMAL and settings_list:
            intersect = set(settings_list[0].tags)
            union = set(settings_list[0].tags)
            for st in settings_list[1:]:
                intersect &= st.tags
                union |= st.tags
            for code, cb in self.tag_panel.checkbox_map.items():
                cb.blockSignals(True)
                if code in intersect:
                    cb.set_preselected(False)
                    cb.setChecked(True)
                elif code in union:
                    cb.set_preselected(True)
                    cb.setChecked(False)
                else:
                    cb.set_preselected(False)
                    cb.setChecked(False)
                cb.blockSignals(False)

        # Load preview for the currently focused row
        item_to_preview = self.table_widget.item(current_row, 1)
        if item_to_preview:
            path_to_preview = item_to_preview.data(int(Qt.ItemDataRole.UserRole))
            # Avoid reloading the same path repeatedly
            if path_to_preview != getattr(self.media_viewer, "current_media_path", None):
                self.load_preview(path_to_preview)

        self.table_widget.sync_check_column()
        self.update_status()

    def save_current_item_settings(self):
        rows = [idx.row() for idx in self.table_widget.selectionModel().selectedRows()]
        if not rows:
            return
        self.table_widget.setSortingEnabled(False)
        checkbox_states = {code: cb.checkbox.checkState() for code, cb in self.tag_panel.checkbox_map.items()}
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
        self._session_save_timer.start()

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
                settings = ItemSettings(item0.data(int(Qt.ItemDataRole.UserRole)))
                item0.setData(ROLE_SETTINGS, settings)
            if check_state in (Qt.Checked, Qt.PartiallyChecked):
                settings.tags.add(code)
            elif check_state == Qt.Unchecked:
                settings.tags.discard(code)
            tags_str = ",".join(sorted(settings.tags))
            # Ensure the tags cell exists
            cell_tags = self.table_widget.item(row, 2)
            if not cell_tags:
                cell_tags = QTableWidgetItem()
                self.table_widget.setItem(row, 2, cell_tags)
            # Update text without triggering on_table_item_changed
            self._ignore_table_changes = True
            try:
                cell_tags.setText(tags_str)
                cell_tags.setToolTip(tags_str)
            finally:
                self._ignore_table_changes = False
            self.update_row_background(row, settings)
        self.table_widget.sync_check_column()
        QTimer.singleShot(0, self.on_table_selection_changed)
        self._session_save_timer.start()

    def update_row_background(self, row: int, settings: ItemSettings):
        # Refresh cells for tags, date, and suffix based on current settings
        # Tags column
        if self.rename_mode == MODE_NORMAL:
            cell_tags = self.table_widget.item(row, 2)
            if cell_tags:
                tags_str = ",".join(sorted(settings.tags))
                cell_tags.setText(tags_str)
                cell_tags.setToolTip(tags_str)
            # Date column
            cell_date = self.table_widget.item(row, 3)
            if cell_date:
                cell_date.setText(settings.date)
                cell_date.setToolTip(settings.date)
        # Suffix column (both modes)
        cell_suffix = self.table_widget.item(row, 4)
        if cell_suffix:
            cell_suffix.setText(settings.suffix)
            cell_suffix.setToolTip(settings.suffix)
    
    def _on_paths_added(self, count: int) -> None:
        """Refresh display of tags, date, and suffix for all rows after import."""
        for row in range(self.table_widget.rowCount()):
            item0 = self.table_widget.item(row, 1)
            if not item0:
                continue
            settings: ItemSettings = item0.data(ROLE_SETTINGS)
            if not settings:
                continue
            self.update_row_background(row, settings)

    def on_table_item_changed(self, item: QTableWidgetItem):
        if self._ignore_table_changes:
            return
        # preserve multi-row selection before edit
        prev_rows = {idx.row() for idx in self.table_widget.selectionModel().selectedRows()}
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
            try:
                raw_tags = {t.strip().upper() for t in item.text().split(',') if t.strip()}
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
            except Exception as e:
                logging.getLogger(__name__).error(f"Error validating tags: {e}")
            # skip preview update to avoid crash during editing
            self._session_save_timer.start()
            return
        elif self.rename_mode == MODE_NORMAL and col == 3:
            text = item.text().strip()
            formatted_date = _validate_and_format_date(text)
            if not formatted_date:
                QMessageBox.warning(
                    self,
                    tr("invalid_date_title"),
                    tr("invalid_date_msg"),
                )
                self._ignore_table_changes = True
                item.setText(settings.date)
                self._ignore_table_changes = False
            else:
                settings.date = formatted_date
                item.setText(formatted_date)
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
        self.update_row_background(row, settings)
        # restore multi-row selection to survive edits
        sel_model = self.table_widget.selectionModel()
        for r in prev_rows:
            idx0 = self.table_widget.model().index(r, 0)
            sel_model.select(idx0, QItemSelectionModel.Select | QItemSelectionModel.Rows)
        # update preview only if current row was edited
        if row in prev_rows:
            self.on_table_selection_changed()
        self._session_save_timer.start()

    def load_preview(self, path: str):
        """Load preview image/video using a background thread."""
        self.logger.debug("Request to load preview for: %s", path)
        self._last_preview_path = path or ""
        
        # Clear previous pixmap from cache if a new path is being loaded
        if self.media_viewer.current_media_path and self.media_viewer.current_media_path != path:
            QPixmapCache.remove(self.media_viewer.current_media_path)
            self.logger.debug(f"Removed {self.media_viewer.current_media_path} from QPixmapCache.")

        # If a load is already running, queue the request as pending and return.
        if self._preview_loader and self._is_preview_loading:
            self.logger.debug("Preview already loading; queueing pending request for %s", path)
            self._pending_preview_path = path
            return

        if not path:
            self.media_viewer.load_path("")
            return

        # Check if it's a video file - handle directly without background thread
        ext = os.path.splitext(path)[1].lower()
        if ext in MediaViewer.VIDEO_EXTS:
            self.media_viewer.load_path(path)
            return

        # Handle images with background loading and caching
        try:
            pix = QPixmap()
            if QPixmapCache.find(path, pix) and not pix.isNull():
                self.media_viewer.show_pixmap(pix)
                return
        except Exception:
            # Fallback: ignore cache if API signature differs
            pass

        # Issue a request to the persistent loader
        if self._preview_loader and self._preview_thread and self._preview_thread.isRunning():
            self._is_preview_loading = True
            # Call queued-slot on worker thread
            self._preview_loader.request(path, self.media_viewer.size())
        else:
            self.logger.warning("Preview worker not available; loading directly on UI thread as fallback.")
            # UI-thread fallback: minimal load using QImageReader
            reader = QImageReader(path)
            reader.setAutoTransform(True)
            image = reader.read()
            if image.isNull():
                placeholder = self.media_viewer.image_viewer.placeholder_pixmap
                self.media_viewer.show_pixmap(placeholder)
            else:
                self.media_viewer.show_pixmap(QPixmap.fromImage(image))
            self._is_preview_loading = False

    @Slot(str, QImage)
    def _on_preview_loaded(self, path: str, image: QImage) -> None:
        try:
            self.logger.debug("Preview loaded for: %s (last requested: %s)", path, self._last_preview_path)
            # Ignore stale results that do not match the latest requested path
            if path != (self._last_preview_path or ""):
                self.logger.debug("Ignoring stale preview for: %s", path)
                # If there is still a pending request, ensure it is started next
                next_req = self._pending_preview_path
                self._pending_preview_path = None
                if next_req:
                    self.load_preview(next_req)
                return

            # Mark loader as available for the next request
            self._is_preview_loading = False

            if image.isNull():
                logging.getLogger(__name__).warning("Failed to load preview: %s", path)
                placeholder = self.media_viewer.image_viewer.placeholder_pixmap
                self.media_viewer.show_pixmap(placeholder)
                # Chain next pending request if present
                next_req = self._pending_preview_path
                self._pending_preview_path = None
                if next_req:
                    self.load_preview(next_req)
                return
            pixmap = QPixmap.fromImage(image)
            try:
                QPixmapCache.insert(path, pixmap)
            except Exception:
                # Cache insert may fail if key too long or cache issues; ignore
                pass
            self.media_viewer.show_pixmap(pixmap)
            # If we have a pending request queued, start it now (latest wins semantics)
            next_req = self._pending_preview_path
            self._pending_preview_path = None
            if next_req and next_req != path:
                self.load_preview(next_req)
        except Exception as e:
            self.logger.exception(f"Unhandled error in _on_preview_loaded for {path}: {e}")

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
        self.mode_tabs.normal_tab.setRowCount(0)
        self.mode_tabs.position_tab.setRowCount(0)
        self.mode_tabs.pa_mat_tab.setRowCount(0)
        self.media_viewer.load_path("")
        for cb in self.tag_panel.checkbox_map.values():
            cb.setChecked(False)
        self.set_item_controls_enabled(False)
        self.update_status()
        QPixmapCache.clear() # Clear the pixmap cache
        self.logger.debug("QPixmapCache cleared in clear_all.")
        self._session_save_timer.start()

    def clear_cache(self):
        QPixmapCache.clear()
        self.logger.debug("QPixmapCache cleared.")

    def undo_rename(self):
        if not self.undo_manager.has_history():
            QMessageBox.information(self, tr("undo_nothing_title"), tr("undo_nothing_msg"))
            return
        undone = self.undo_manager.undo_all()
        for row, orig in undone:
            for table in [self.mode_tabs.normal_tab, self.mode_tabs.position_tab, self.mode_tabs.pa_mat_tab]:
                if 0 <= row < table.rowCount():
                    item0 = table.item(row, 1)
                    if item0:
                        item0.setText(os.path.basename(orig))
                        item0.setData(int(Qt.ItemDataRole.UserRole), orig)
        QMessageBox.information(self, tr("done"), tr("undo_done"))
        self._session_save_timer.start()

    def remove_selected_items(self):
        rows = sorted({idx.row() for idx in self.table_widget.selectionModel().selectedRows()}, reverse=True)
        for row in rows:
            self.mode_tabs.normal_tab.removeRow(row)
            self.mode_tabs.position_tab.removeRow(row)
            self.mode_tabs.pa_mat_tab.removeRow(row)
        if self.table_widget.rowCount() == 0:
            self.media_viewer.load_path("")
            self.set_item_controls_enabled(False)
        else:
            new_row = min(rows[0], self.table_widget.rowCount() - 1)
            self.table_widget.selectRow(new_row)
        self.update_status()
        self._session_save_timer.start()

    def delete_selected_files(self):
        """Permanently deletes the selected files from the disk after confirmation."""
        rows = sorted({idx.row() for idx in self.table_widget.selectionModel().selectedRows()})
        if not rows:
            return

        reply = QMessageBox.question(
            self,
            tr("delete_files_title"),
            tr("delete_files_msg").format(count=len(rows)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.No:
            return

        errors = []
        for row in reversed(rows):
            item = self.table_widget.item(row, 1)
            if not item:
                continue

            path_str = item.data(int(Qt.ItemDataRole.UserRole))
            path = Path(path_str)
            try:
                path.unlink()
                self.logger.info(f"Deleted file: {path}")
            except OSError as e:
                self.logger.error(f"Error deleting file {path}: {e}")
                errors.append((path.name, str(e)))

        if errors:
            error_msg = "\n".join([f"- {name}: {err}" for name, err in errors])
            QMessageBox.warning(
                self, tr("delete_failed_title"), tr("delete_failed_msg").format(errors=error_msg)
            )

        self.remove_selected_items()

    def clear_selected_suffixes(self):
        rows = [idx.row() for idx in self.table_widget.selectionModel().selectedRows()]
        self.table_widget.setSortingEnabled(False)
        for row in rows:
            item0 = self.table_widget.item(row, 1)
            if not item0:
                continue
            settings: ItemSettings = item0.data(ROLE_SETTINGS)
            if settings is None:
                settings = ItemSettings(item0.data(int(Qt.ItemDataRole.UserRole)))
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
        self._session_save_timer.start()
    
    def add_suffix_for_selected(self) -> None:
        """Prompt for a suffix and append it to all selected rows."""
        text, ok = QInputDialog.getText(
            self,
            tr("add_suffix"),
            tr("enter_suffix")
        )
        if not ok or not text:
            return
        suffix_to_append = text.strip()
        rows = [idx.row() for idx in self.table_widget.selectionModel().selectedRows()]
        if not rows:
            return
        self.table_widget.setSortingEnabled(False)
        for row in rows:
            item0 = self.table_widget.item(row, 1)
            if not item0:
                continue
            settings: ItemSettings = item0.data(ROLE_SETTINGS)
            if settings is None:
                settings = ItemSettings(item0.data(int(Qt.ItemDataRole.UserRole)))
                item0.setData(ROLE_SETTINGS, settings)
            # Append suffix
            settings.suffix += suffix_to_append
            cell = self.table_widget.item(row, 4)
            if not cell:
                cell = QTableWidgetItem()
                self.table_widget.setItem(row, 4, cell)
            self._ignore_table_changes = True
            try:
                cell.setText(settings.suffix)
                cell.setToolTip(settings.suffix)
            finally:
                self._ignore_table_changes = False
            self.update_row_background(row, settings)
        self.table_widget.sync_check_column()
        self.on_table_selection_changed()
        self._session_save_timer.start()

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
            path = item0.data(int(Qt.ItemDataRole.UserRole))
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
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            convert_heic = reply == QMessageBox.StandardButton.Yes
        from .compression_dialog import CompressionDialog
        dlg = CompressionDialog(
            paths,
            convert_heic,
            parent=self,
            state_manager=self.state_manager,
        )
        if dlg.exec() == QDialog.Accepted:
            for row, new_path, size_bytes, compressed_bytes in dlg.final_results:
                for table in [self.mode_tabs.normal_tab, self.mode_tabs.position_tab, self.mode_tabs.pa_mat_tab]:
                    item0 = table.item(row, 1)
                    item0.setData(int(Qt.ItemDataRole.UserRole), new_path)
                    item0.setText(os.path.basename(new_path))
                    st: ItemSettings = item0.data(ROLE_SETTINGS)
                    if st:
                        st.size_bytes = size_bytes
                        st.compressed_bytes = compressed_bytes
            self._session_save_timer.start()

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

        converted = 0
        for i, row in enumerate(rows):
            if progress.wasCanceled():
                break
            item0 = self.table_widget.item(row, 1)
            if not item0:
                continue
            path = item0.data(int(Qt.ItemDataRole.UserRole))
            new_path = convert_to_jpeg(path)
            if new_path != path:
                for table in [self.mode_tabs.normal_tab, self.mode_tabs.position_tab, self.mode_tabs.pa_mat_tab]:
                    item0 = table.item(row, 1)
                    item0.setData(int(Qt.ItemDataRole.UserRole), new_path)
                    item0.setText(os.path.basename(new_path))
                    st: ItemSettings = item0.data(ROLE_SETTINGS)
                    if st:
                        st.size_bytes = os.path.getsize(new_path)
                        st.compressed_bytes = st.size_bytes
                if row == self.table_widget.currentRow():
                    self.load_preview(new_path)
                converted += 1
            progress.setValue(i + 1)
            QApplication.processEvents()

        progress.close()
        QMessageBox.information(
            self,
            tr("done"),
            f"Converted {converted} of {total} images to JPEG."
        )
        self._session_save_timer.start()

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
            settings: ItemSettings = item0.data(ROLE_SETTINGS)
            if settings is None:
                path = item0.data(int(Qt.ItemDataRole.UserRole))
                settings = ItemSettings(path)
                item0.setData(ROLE_SETTINGS, settings)
            items.append(settings)

        renamer = Renamer(project, items, dest_dir=dest_dir, mode=self.rename_mode)
        mapping = renamer.build_mapping()
        return mapping
    
    def build_full_rename_mapping(self, dest_dir: str | None = None):
        """Build rename mapping for all items in all mode tabs."""
        project = self.input_project.text().strip()
        if not re.fullmatch(r"C\d{6}", project):
            QMessageBox.warning(self, tr("missing_project"), tr("missing_project_msg"))
            return None
        full = []
        # iterate through each mode tab
        for mode, table in [(MODE_NORMAL, self.mode_tabs.normal_tab),
                            (MODE_POSITION, self.mode_tabs.position_tab),
                            (MODE_PA_MAT, self.mode_tabs.pa_mat_tab)]:
            # collect item settings for this mode
            items = []
            for row in range(table.rowCount()):
                item0 = table.item(row, 1)
                if not item0:
                    continue
                settings: ItemSettings = item0.data(ROLE_SETTINGS)
                if settings is None:
                    path = item0.data(int(Qt.ItemDataRole.UserRole))
                    settings = ItemSettings(path)
                items.append(settings)
            if not items:
                continue
            renamer = Renamer(project, items, dest_dir=dest_dir, mode=mode)
            mapping = renamer.build_mapping()
            for settings, orig, new in mapping:
                settings.new_path = new # Set new_path attribute
                full.append((mode, settings, orig, new))
        return full

    def build_active_tab_rename_mapping(self, dest_dir: str | None = None):
        """Build rename mapping only for items in the currently active mode tab."""
        project = self.input_project.text().strip()
        if not re.fullmatch(r"C\d{6}", project):
            QMessageBox.warning(self, tr("missing_project"), tr("missing_project_msg"))
            return None

        active_mode = self.rename_mode
        active_table = getattr(self.mode_tabs, f"{active_mode}_tab")

        items = []
        for row in range(active_table.rowCount()):
            item0 = active_table.item(row, 1)
            if not item0:
                continue
            settings: ItemSettings = item0.data(ROLE_SETTINGS)
            if settings is None:
                path = item0.data(int(Qt.ItemDataRole.UserRole))
                settings = ItemSettings(path)
            items.append(settings)

        if not items:
            return []

        renamer = Renamer(project, items, dest_dir=dest_dir, mode=active_mode)
        mapping = renamer.build_mapping()
        
        # The mapping from renamer.build_mapping() is (settings, orig, new)
        # We need to convert it to (mode, settings, orig, new) for consistency with full mapping
        full_mapping = []
        for settings, orig, new in mapping:
            settings.new_path = new # Set new_path attribute
            full_mapping.append((active_mode, settings, orig, new))
        return full_mapping
    
    def rename_selected(self):
        """Rename only the selected files using current project and mode."""
        rows = [idx.row() for idx in self.table_widget.selectionModel().selectedRows()]
        self.logger.debug(f"rename_selected: Selected rows: {rows}") # Add logging here
        project = self.input_project.text().strip()
        # collect settings for selected rows
        items = []
        for row in rows:
            item0 = self.table_widget.item(row, 1)
            if not item0:
                continue
            settings = item0.data(ROLE_SETTINGS)
            if settings:
                items.append(settings)
        if not items:
            return
        # build rename mapping for selected items
        renamer = Renamer(project, items, mode=self.rename_mode)
        mapping = renamer.build_mapping()
        # prepare final mapping with row indices
        final_mapping = []
        for settings, orig, new_path in mapping:
            # find corresponding row
            for row in rows:
                item0 = self.table_widget.item(row, 1)
                if item0 and item0.data(int(Qt.ItemDataRole.UserRole)) == orig:
                    final_mapping.append((row, orig, os.path.basename(new_path), new_path))
                    break
        self.execute_rename_with_progress(final_mapping)

    def choose_save_directory(self) -> str | None:
        reply = QMessageBox.question(
            self,
            tr('use_original_directory'),
            tr('use_original_directory_msg'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            return None
        directory = QFileDialog.getExistingDirectory(
            self,
            tr('default_save_dir_label'),
            config_manager.get('default_save_directory', '')
        )
        if directory:
            config_manager.set('default_save_directory', directory)
        return directory or None

    def _start_rename_from_preview(self, table_mapping: list[tuple[str, int, str, str, str]]):
        """Handle the rename process after preview confirmation."""
        dlg = RenameOptionsDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return

        dest_dir = dlg.directory
        compress = dlg.compress_after
        config_manager.set("compress_after_rename", compress)
        if dest_dir:
            config_manager.set("default_save_directory", dest_dir)

        final_table_mapping = []
        if dest_dir:
            for mode, row, orig, new_name, old_new_path in table_mapping:
                new_path = os.path.join(dest_dir, new_name)
                final_table_mapping.append((row, orig, new_name, new_path))
        else:
            for mode, row, orig, new_name, new_path in table_mapping:
                final_table_mapping.append((row, orig, new_name, new_path))
        
        self.execute_rename_with_progress(final_table_mapping, compress=compress)
        self.logger.info(f"Final table mapping for execution: {final_table_mapping}")

    def preview_rename(self):
        # build mapping for the active tab only
        mapping = self.build_active_tab_rename_mapping()
        if not mapping:
            QMessageBox.information(self, tr("no_files"), tr("no_files_msg"))
            self.logger.warning("No mapping generated. Aborting preview.")
            return

        # prepare mapping entries: (mode, row, orig_path, new_name, new_path)
        table_mapping: list[tuple[str,int,str,str,str]] = []
        for mode, settings, orig, new in mapping:
            new_name = os.path.basename(new)
            # Use the active table directly, as mapping is already for the active tab
            active_table = getattr(self.mode_tabs, f"{mode}_tab")
            for row in range(active_table.rowCount()):
                item0 = active_table.item(row, 1)
                if item0 and item0.data(int(Qt.ItemDataRole.UserRole)) == orig:
                    table_mapping.append((mode, row, orig, new_name, new))
                    break
        self.logger.info(f"Table mapping for preview: {table_mapping}")
        
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("preview_rename"))
        if self.state_manager:
            w = self.state_manager.get("preview_width", 800)
            h = self.state_manager.get("preview_height", 600)
            dlg.resize(w, h)
        
        dlg_layout = QVBoxLayout(dlg)
        # explanatory info
        info = QLabel(
            "Rename All: renames all files previewed.\n"
            "Rename Selected: renames only files selected in the main window."
        )
        info.setWordWrap(True)
        dlg_layout.addWidget(info)
        
        # preview table: Mode, Current Name, Proposed New Name
        tbl = QTableWidget(len(table_mapping), 3, dlg)
        tbl.setHorizontalHeaderLabels([
            tr("mode"),
            tr("current_name"),
            tr("proposed_new_name"),
        ])
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        tbl.setSelectionBehavior(QTableWidget.SelectRows)
        tbl.setSelectionMode(QTableWidget.ExtendedSelection)

        for i, (mode, row, orig, new_name, new_path) in enumerate(table_mapping):
            tbl.setItem(i, 0, QTableWidgetItem(tr(f"mode_{mode}")))
            tbl.setItem(i, 1, QTableWidgetItem(os.path.basename(orig)))
            tbl.setItem(i, 2, QTableWidgetItem(new_name))

        tbl.resizeColumnsToContents()
        tbl.resizeRowsToContents()
        tbl.setMinimumWidth(600)
        # auto-select first row so Rename Selected has a target
        if tbl.rowCount() > 0:
            tbl.selectRow(0)
        dlg_layout.addWidget(tbl)

        btns = QDialogButtonBox(parent=dlg)
        btn_rename_all = btns.addButton(tr("rename_all"), QDialogButtonBox.AcceptRole)
        btn_rename_selected = btns.addButton(tr("rename_selected"), QDialogButtonBox.ActionRole)
        btns.addButton(QDialogButtonBox.Cancel)

        def on_rename_all():
            dlg.accept()
            self._start_rename_from_preview(table_mapping)

        def on_rename_selected():
            # Use main window selection, not preview table
            main_selected = {idx.row() for idx in self.table_widget.selectionModel().selectedRows()}
            if not main_selected:
                QMessageBox.information(self, tr("information"), tr("no_items_selected"))
                return
            # Filter mapping for current mode and selected rows
            selected_mapping = [
                (mode, row, orig, new_name, new_path)
                for (mode, row, orig, new_name, new_path) in table_mapping
                if mode == self.rename_mode and row in main_selected
            ]
            if not selected_mapping:
                QMessageBox.information(self, tr("information"), tr("no_items_selected"))
                return
            dlg.accept()
            self._start_rename_from_preview(selected_mapping)

        btn_rename_all.clicked.connect(on_rename_all)
        btn_rename_selected.clicked.connect(on_rename_selected)
        btns.rejected.connect(dlg.reject)
        dlg_layout.addWidget(btns)

        dlg.exec()

        if self.state_manager:
            self.state_manager.set("preview_width", dlg.width())
            self.state_manager.set("preview_height", dlg.height())
            self.state_manager.save()

    def direct_rename(self, table_mapping: list):
        self.rename_with_options(table_mapping, all_items=True)

    def direct_rename_selected(self, table_mapping: list):
        selected_rows = {
            idx.row() for idx in self.table_widget.selectionModel().selectedRows()
        }
        selected_mapping = [
            item for item in table_mapping if item[0] in selected_rows
        ]
        self.rename_with_options(selected_mapping, all_items=False)

    def choose_save_directory_and_rename(
        self, table_mapping: list, all_items: bool
    ):
        dlg = RenameOptionsDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        dest = dlg.directory
        compress = dlg.compress_after
        config_manager.set("compress_after_rename", compress)
        if dest:
            config_manager.set("default_save_directory", dest)

        if all_items:
            rows = list(range(self.table_widget.rowCount()))
        else:
            rows = [item[0] for item in table_mapping]

        mapping = self.build_rename_mapping(dest, rows)
        if mapping is None:
            return

        # Create a new table_mapping with the updated destination paths
        final_table_mapping = []
        for _, orig, new_dest_path in mapping:
            for row, orig_path, _, _ in table_mapping:
                if orig_path == orig:
                    final_table_mapping.append(
                        (row, orig, os.path.basename(new_dest_path), new_dest_path)
                    )
                    break
        self.execute_rename_with_progress(final_table_mapping, compress=compress)

    def rename_with_options(self, table_mapping: list, all_items: bool = True):
        self.choose_save_directory_and_rename(table_mapping, all_items)

    def _execute_full_rename(self, table_mapping: list[tuple[str,int,str,str,str]]) -> None:
        """Perform file renames for all mappings across all tabs."""
        total = len(table_mapping)
        done = 0
        for mode, row, orig, new_name, new_path in table_mapping:
            try:
                os.rename(orig, new_path)
                done += 1
                # update table item
                table = getattr(self.mode_tabs, f"{mode}_tab")
                item0 = table.item(row, 1)
                if item0:
                    item0.setData(int(Qt.ItemDataRole.UserRole), new_path)
                    item0.setText(new_name)
                    settings: ItemSettings = item0.data(ROLE_SETTINGS)
                    if settings:
                        settings.original_path = new_path
            except Exception as e:
                logging.getLogger(__name__).error(f"Error renaming {orig} to {new_path}: {e}")
                QMessageBox.warning(self, tr("rename_failed"), f"{orig} -> {new_name}")
        # show result
        if done < total:
            QMessageBox.information(self, tr("partial_rename"), tr("partial_rename_msg").format(done=done, total=total))
        else:
            QMessageBox.information(self, tr("done"), tr("rename_done"))
        self._session_save_timer.start()

    def set_status_message(self, message: str | None) -> None:
        """Display an additional message in the status bar."""
        self.status_message = message or ""
        self.update_status()

    def execute_rename_with_progress(self, table_mapping, compress: bool = False):
        """Executes the renaming process with a progress dialog."""
        self.media_viewer.clear_media()
        self.set_status_message(tr("renaming_files"))
        self.table_widget.setSortingEnabled(False)

        progress = self._create_progress_dialog(tr("renaming_files"), len(table_mapping))
        compressor = self._get_compressor() if compress else None

        results = self._perform_rename_operations(table_mapping, progress, compressor)

        progress.close()
        self._process_rename_results(results, progress.wasCanceled(), self.rename_mode)

        self.set_status_message(None)
        self._enable_sorting()
        self._session_save_timer.start()

    def _create_progress_dialog(self, title: str, total: int) -> QProgressDialog:
        """Creates and configures a progress dialog."""
        progress = QProgressDialog(title, tr("abort"), 0, total, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(200)
        progress.setValue(0)
        return progress

    def _get_compressor(self) -> ImageCompressor | None:
        """Creates an ImageCompressor instance based on current settings."""
        try:
            cfg = config_manager.load()
            return ImageCompressor(
                max_size_kb=cfg.get("compression_max_size_kb", 2048),
                quality=cfg.get("compression_quality", 95),
                reduce_resolution=cfg.get("compression_reduce_resolution", True),
                resize_only=cfg.get("compression_resize_only", False),
                max_width=cfg.get("compression_max_width", 0) or None,
                max_height=cfg.get("compression_max_height", 0) or None,
            )
        except Exception as e:
            self.logger.error(f"Failed to create ImageCompressor: {e}")
            return None

    def _perform_rename_operations(
        self, table_mapping: list[tuple[int, str, str, str]], progress: QProgressDialog, compressor: ImageCompressor | None
    ) -> list[dict]:
        """Iterates through the mapping and performs the rename and compression."""
        results = []
        for idx, (row, orig_path, new_name, new_path) in enumerate(table_mapping):
            # Ensure new_path is absolute
            if not Path(new_path).is_absolute():
                new_path = str(Path(orig_path).parent / new_path)

            if progress.wasCanceled():
                break

            result = {
                "row": row,
                "orig": orig_path,
                "new": new_path,
                "old_size": None,
                "new_size": None,
                "error": None,
            }

            try:
                orig_path_obj = Path(orig_path)
                new_path_obj = Path(new_path)

                if orig_path_obj.resolve() != new_path_obj.resolve():
                    # Attempt to rename the file
                    try:
                        orig_path_obj.rename(new_path_obj)
                    except FileExistsError:
                        # If the destination file already exists, try to remove it first
                        # This might happen if a previous rename failed partially
                        self.logger.warning(f"Destination file {new_path_obj} already exists. Attempting to remove it.")
                        try:
                            new_path_obj.unlink()
                            orig_path_obj.rename(new_path_obj)
                        except Exception as unlink_e:
                            raise Exception(f"Failed to remove existing destination file {new_path_obj}: {unlink_e}") from unlink_e
                    except Exception as rename_e:
                        raise Exception(f"Failed to rename file from {orig_path_obj} to {new_path_obj}: {rename_e}") from rename_e

                final_path = new_path_obj
                if compressor and new_path_obj.suffix.lower() not in MediaViewer.VIDEO_EXTS:
                    old_size = new_path_obj.stat().st_size
                    # Ensure the compressor handles the file path correctly and doesn't leave it locked
                    final_path, new_size, _ = compressor.compress(str(new_path_obj))
                    result["old_size"] = old_size
                    result["new_size"] = new_size
                result["new"] = Path(final_path)

            except Exception as e:
                self.logger.exception(f"Error processing {orig_path} -> {new_path}") # Log full traceback
                result["error"] = str(e)

            results.append(result)
            progress.setValue(idx + 1)
            QApplication.processEvents()
        return results

    def _process_rename_results(self, results: list[dict], was_canceled: bool, active_mode: str):
        """Processes the results of the rename operations, updating the UI."""
        used_tags: list[str] = []
        successful_renames = 0
        rows_to_remove = []

        for res in results:
            if res.get("error"):
                QMessageBox.warning(
                    self,
                    tr("rename_failed"),
                    f"""Error renaming:
Original: {res['orig']}
New: {res['new']}
Error: {res['error']} """
                )
                continue

            successful_renames += 1
            row = res["row"]
            new_path = res["new"]
            rows_to_remove.append(row)

            for table in self.mode_tabs.all_tables():
                item0 = table.item(row, 1)
                if item0:
                    item0.setText(new_path.name)
                    item0.setData(int(Qt.ItemDataRole.UserRole), str(new_path))
                    settings = item0.data(ROLE_SETTINGS)
                    if settings and self.rename_mode == MODE_NORMAL:
                        used_tags.extend(settings.tags)
                    self.undo_manager.record(row, str(res["orig"]), str(new_path))
                    if res.get("old_size") is not None:
                        if settings:
                            settings.size_bytes = res.get("old_size")
                            settings.compressed_bytes = res.get("new_size")

        # Remove successfully renamed rows from the table
        active_table = getattr(self.mode_tabs, f"{active_mode}_tab")
        for row in sorted(rows_to_remove, reverse=True):
            active_table.removeRow(row)

        if was_canceled:
            QMessageBox.information(
                self,
                tr("partial_rename"),
                tr("partial_rename_msg").format(done=successful_renames, total=len(results))
            )
        else:
            QMessageBox.information(self, tr("done"), tr("rename_done"))
            if used_tags and self.rename_mode == MODE_NORMAL:
                increment_tags(used_tags)
                self.tag_panel.rebuild()

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

    def save_session(self):
        """Saves the current state of the application to a session file."""
        self.logger.info("Saving session...")
        session_file = Path(config_manager.config_dir) / "session.json"
        data = {
            "project_number": self.input_project.text(),
            "files": []
        }

        for row in range(self.mode_tabs.normal_tab.rowCount()):
            item = self.mode_tabs.normal_tab.item(row, 1)
            if not item:
                continue
            settings: ItemSettings = item.data(ROLE_SETTINGS)
            if not settings:
                continue
            data["files"].append(settings.to_dict())

        try:
            with open(session_file, "w") as f:
                json.dump(data, f, indent=2)
            self.logger.info("Session saved successfully.")
            self.set_session_status(True)
        except (IOError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to save session: {e}")
            QMessageBox.warning(self, tr("error"), tr("session_save_failed").format(error=e))

    def check_for_crashed_session(self):
        """Checks for a crashed session file and prompts the user to restore it."""
        session_file = Path(config_manager.config_dir) / "session.json"
        if not session_file.exists():
            return

        reply = QMessageBox.question(
            self,
            tr("restore_session_title"),
            tr("restore_session_msg"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.restore_session(show_dialog=False)
        else:
            if session_file.exists():
                try:
                    session_file.unlink()
                except OSError as e:
                    self.logger.error(f"Failed to remove session file: {e}")

    def restore_session(self, show_dialog=True):
        """Restores the application state from a session file."""
        session_file = Path(config_manager.config_dir) / "session.json"
        if not session_file.exists():
            if show_dialog:
                QMessageBox.information(
                    self,
                    tr("restore_session_title"),
                    tr("no_session_to_restore"),
                )
            return

        if show_dialog:
            reply = QMessageBox.question(
                self,
                tr("restore_session_title"),
                tr("restore_session_msg"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return

        try:
            with open(session_file, "r") as f:
                data = json.load(f)

            self.input_project.setText(data.get("project_number", ""))

            paths_to_add, settings_map = self._prepare_restored_files(data)

            if paths_to_add:
                for table in self.mode_tabs.all_tables():
                    table.add_paths(paths_to_add)

            self._apply_restored_settings(settings_map)

            self.logger.info("Session restored successfully.")
            self._session_recording_started = True
            QMessageBox.information(
                self,
                tr("restore_session_title"),
                tr("session_restored_successfully"),
            )
        except (IOError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to restore session: {e}")
            QMessageBox.warning(
                self,
                tr("restore_session_title"),
                tr("session_restore_failed").format(error=e),
            )
        finally:
            if session_file.exists() and not show_dialog:
                try:
                    session_file.unlink()
                except OSError as e:
                    self.logger.error(f"Failed to remove session file: {e}")

    def _prepare_restored_files(self, data: dict) -> tuple[list[str], dict[str, ItemSettings]]:
        """Prepares the list of files and settings to be restored."""
        paths_to_add = []
        settings_map = {}
        for item_data in data.get("files", []):
            try:
                settings = ItemSettings.from_dict(item_data)
                if Path(settings.original_path).exists():
                    paths_to_add.append(settings.original_path)
                    settings_map[settings.original_path] = settings
                else:
                    self.logger.warning(f"File not found, skipping: {settings.original_path}")
            except Exception as e:
                self.logger.error(f"Failed to restore item: {item_data}. Error: {e}")
        return paths_to_add, settings_map

    def _apply_restored_settings(self, settings_map: dict[str, ItemSettings]):
        """Applies the restored settings to the table."""
        for row in range(self.mode_tabs.normal_tab.rowCount()):
            item = self.mode_tabs.normal_tab.item(row, 1)
            if not item:
                continue
            path = item.data(int(Qt.ItemDataRole.UserRole))
            if path in settings_map:
                settings = settings_map[path]
                for table in self.mode_tabs.all_tables():
                    table.item(row, 1).setData(ROLE_SETTINGS, settings)
                    table.item(row, 2).setText(",".join(sorted(settings.tags)))
                    table.item(row, 3).setText(settings.date)
                    table.item(row, 4).setText(settings.suffix)
                    self.update_row_background(row, settings)

    def closeEvent(self, event):
        """Handles the application closing event."""
        self.logger.info("Close event triggered.")
        if self._preview_loader:
            try:
                self.logger.debug("Stopping preview loader on close.")
                self._preview_loader.stop()
            except Exception:
                pass
        if self._preview_thread and self._preview_thread.isRunning():
            try:
                self.logger.debug("Waiting for preview thread to finish on close.")
                self._preview_thread.quit()
                self._preview_thread.wait(2000)
            except Exception:
                pass

        if self.state_manager:
            self.state_manager.set("width", self.width())
            self.state_manager.set("height", self.height())
            self.state_manager.set("splitter_sizes", self.splitter.sizes())
            self.state_manager.save()

        if self.media_viewer.video_player.player:
            self.media_viewer.video_player.player.stop()

        # On clean shutdown, remove the session file
        session_file = Path(config_manager.config_dir) / "session.json"
        if session_file.exists():
            try:
                session_file.unlink()
            except OSError as e:
                self.logger.error(f"Failed to remove session file on exit: {e}")

        super().closeEvent(event)
