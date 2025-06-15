import os
import re
from PySide6.QtWidgets import (
    QWidget, QSplitter, QHBoxLayout, QVBoxLayout, QGridLayout,
    QPushButton, QSlider, QFileDialog, QMessageBox, QToolBar,
    QGraphicsView, QGraphicsScene, QStyle,
    QApplication, QLabel, QLineEdit,
    QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressDialog, QDialog, QDialogButtonBox, QAbstractItemView
)
from PySide6.QtGui import QPixmap, QPainter, QColor, QAction, QIcon
from PySide6.QtCore import Qt, QTimer, QItemSelectionModel, QItemSelection

from .. import config, save_config
from ..config.app_config import load_config
from ..utils.i18n import tr, set_language
from .settings_dialog import SettingsDialog
from ..logic.settings import ItemSettings
from ..logic.renamer import Renamer
from ..logic.tag_loader import load_tags

ROLE_SETTINGS = Qt.UserRole + 1

class ImageViewer(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        scene = QGraphicsScene(self)
        self.setScene(scene)
        self.pixmap_item = None
        self.current_pixmap = None
        # Drag-Pan aktivieren
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        # Zoom-Anker unter Maus
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        # Glättung beim Skalieren
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        # Zoom und Rotation intern tracken
        self._zoom_pct = 100
        self._rotation = 0  # in Grad, 0/90/180/270 etc.
        # Focus, damit wheelEvent nur wirkt, wenn Maus über ImageViewer ist
        self.setFocusPolicy(Qt.StrongFocus)

    def load_image(self, path: str):
        if not path:
            self.scene().clear()
            self.pixmap_item = None
            self.current_pixmap = None
            # Reset intern, aber behalte keine Rotation für neuen Bild-Load:
            self._zoom_pct = 100
            self._rotation = 0
            self.reset_transform()
            return
        pix = QPixmap(path)
        if pix.isNull():
            self.scene().clear()
            self.pixmap_item = None
            self.current_pixmap = None
            self._zoom_pct = 100
            self._rotation = 0
            self.reset_transform()
            return
        self.current_pixmap = pix
        self.scene().clear()
        self.pixmap_item = self.scene().addPixmap(pix)
        self.scene().setSceneRect(self.pixmap_item.boundingRect())
        # Nach Laden: initial Fit und keine Rotation
        self._rotation = 0
        self.zoom_fit()

    def reset_transform(self):
        # Rücksetzen der Transformation und Scrollbars an Anfang
        self.resetTransform()
        # Setze Scrollbars zurück
        try:
            self.horizontalScrollBar().setValue(0)
            self.verticalScrollBar().setValue(0)
        except Exception:
            pass

    def wheelEvent(self, event):
        # Zoom nur bei Maus über ImageViewer
        if not self.pixmap_item:
            return
        delta = event.angleDelta().y()
        if delta > 0:
            self._zoom_pct = min(self._zoom_pct + 10, 500)
        else:
            self._zoom_pct = max(self._zoom_pct - 10, 10)
        self.apply_transformations()
        event.accept()

    def apply_transformations(self):
        if not self.pixmap_item:
            return
        # Reset
        self.resetTransform()
        # Zuerst Rotation, dann Skalierung
        if self._rotation != 0:
            # rotate(angle) rotiert relativ; hier nach resetTransform also absolut ok
            self.rotate(self._rotation)
        factor = self._zoom_pct / 100.0
        self.scale(factor, factor)
        # Scrollbars zurücksetzen, damit obere linke Ecke gezeigt bleibt
        try:
            self.horizontalScrollBar().setValue(0)
            self.verticalScrollBar().setValue(0)
        except Exception:
            pass

    def zoom_fit(self):
        if not self.pixmap_item:
            return
        view_rect = self.viewport().rect()
        scene_rect = self.scene().sceneRect().toRect()
        if scene_rect.isEmpty():
            return
        factor_w = view_rect.width() / scene_rect.width()
        factor_h = view_rect.height() / scene_rect.height()
        factor = min(factor_w, factor_h)
        self._zoom_pct = int(factor * 100)
        self.resetTransform()
        if self._rotation != 0:
            self.rotate(self._rotation)
        self.scale(factor, factor)
        try:
            self.horizontalScrollBar().setValue(0)
            self.verticalScrollBar().setValue(0)
        except Exception:
            pass

    def rotate_left(self):
        if not self.pixmap_item:
            return
        # Update interne Rotation
        self._rotation = (self._rotation - 90) % 360
        self.apply_transformations()

    def rotate_right(self):
        if not self.pixmap_item:
            return
        self._rotation = (self._rotation + 90) % 360
        self.apply_transformations()

class AspectRatioWidget(QWidget):
    def __init__(self, aspect_ratio=16/9, parent=None):
        super().__init__(parent)
        self.aspect_ratio = aspect_ratio
        self._widget = None

    def setWidget(self, widget):
        self._widget = widget
        widget.setParent(self)

    def resizeEvent(self, event):
        if not self._widget:
            return super().resizeEvent(event)
        w = self.width()
        h = self.height()
        target_w = w
        target_h = int(target_w / self.aspect_ratio)
        if target_h > h:
            target_h = h
            target_w = int(target_h * self.aspect_ratio)
        x = (w - target_w) // 2
        y = (h - target_h) // 2
        self._widget.setGeometry(x, y, target_w, target_h)
        super().resizeEvent(event)

class DragDropTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._updating_checks = False
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["", "Filename", "Tags", "Suffix"])
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setStretchLastSection(True)
        header.sectionDoubleClicked.connect(self.on_header_double_clicked)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setAcceptDrops(True)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.ExtendedSelection)
        self.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.verticalHeader().setDefaultSectionSize(24)
        self.itemSelectionChanged.connect(self.sync_check_column)
        self.itemChanged.connect(self.handle_item_changed)
        self._initial_columns = False
        QTimer.singleShot(0, self.set_equal_column_widths)

    def set_equal_column_widths(self):
        if self._initial_columns:
            return
        self._initial_columns = True
        header = self.horizontalHeader()
        total = self.viewport().width() - header.sectionSize(0)
        if total <= 0:
            return
        w = total // 3
        for i in range(1, 4):
            self.setColumnWidth(i, w)

    def on_header_double_clicked(self, index: int):
        header = self.horizontalHeader()
        new_width = header.sizeHintForColumn(index)
        header.resizeSection(index, new_width)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            paths = []
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if os.path.isfile(path):
                    ext = os.path.splitext(path)[1].lower()
                    if ext in ItemSettings.ACCEPT_EXTENSIONS:
                        paths.append(path)
            self.add_paths(paths)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def add_paths(self, paths: list[str]):
        for path in paths:
            duplicate = False
            for row in range(self.rowCount()):
                item = self.item(row, 1)
                if item and item.data(Qt.UserRole) == path:
                    duplicate = True
                    break
            if duplicate:
                continue
            row = self.rowCount()
            self.insertRow(row)
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            check_item.setCheckState(Qt.Unchecked)
            fname_item = QTableWidgetItem(os.path.basename(path))
            fname_item.setData(Qt.UserRole, path)
            fname_item.setBackground(QColor(30, 30, 30))
            fname_item.setForeground(QColor(220, 220, 220))
            tags_item = QTableWidgetItem("")
            suffix_item = QTableWidgetItem("")
            tags_item.setToolTip("")
            suffix_item.setToolTip("")
            self.setItem(row, 0, check_item)
            self.setItem(row, 1, fname_item)
            self.setItem(row, 2, tags_item)
            self.setItem(row, 3, suffix_item)
        if self.rowCount() > 0 and not self.selectionModel().hasSelection():
            self.selectRow(0)

    def sync_check_column(self):
        selected = {idx.row() for idx in self.selectionModel().selectedRows()}
        self._updating_checks = True
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            if not item:
                continue
            item.setCheckState(Qt.Checked if row in selected else Qt.Unchecked)
        self._updating_checks = False

    def handle_item_changed(self, item: QTableWidgetItem):
        if self._updating_checks or item.column() != 0:
            return
        row = item.row()
        index = self.model().index(row, 0)
        mods = QApplication.keyboardModifiers()
        if mods & Qt.ShiftModifier and self.selectionModel().hasSelection():
            cur = self.selectionModel().currentIndex().row()
            start = min(cur, row)
            end = max(cur, row)
            selection = QItemSelection(
                self.model().index(start, 0),
                self.model().index(end, self.columnCount() - 1),
            )
            command = QItemSelectionModel.Select if item.checkState() == Qt.Checked else QItemSelectionModel.Deselect
            self.selectionModel().select(selection, command | QItemSelectionModel.Rows)
        else:
            if item.checkState() == Qt.Checked:
                self.selectionModel().select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
            else:
                self.selectionModel().select(index, QItemSelectionModel.Deselect | QItemSelectionModel.Rows)

class RenamerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("app_title"))

        main_layout = QVBoxLayout(self)

        self.toolbar = QToolBar()
        self.setup_toolbar()
        main_layout.addWidget(self.toolbar)

        # no separate selected file display

        grid = QGridLayout()
        main_layout.addLayout(grid)

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

        self.image_viewer = ImageViewer()
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

        grid.addWidget(viewer_widget, 0, 0)
        grid.addWidget(self.table_widget, 0, 1)

        # Tag container spanning both columns with manual toggle
        self.tag_container = QWidget()
        tag_main_layout = QVBoxLayout(self.tag_container)
        lbl_tags = QLabel(tr("select_tags_label"))
        tag_main_layout.addWidget(lbl_tags)
        self.checkbox_container = QWidget()
        self.tag_layout = QGridLayout(self.checkbox_container)
        self.tag_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_info = {}
        self.checkbox_map = {}
        self.rebuild_tag_checkboxes()
        tag_main_layout.addWidget(self.checkbox_container)

        self.btn_toggle_tags = QPushButton()
        self.btn_toggle_tags.clicked.connect(self.toggle_tag_panel)
        grid.addWidget(self.btn_toggle_tags, 1, 0, 1, 2, Qt.AlignLeft)
        grid.addWidget(self.tag_container, 2, 0, 1, 2)
        self.tag_container.setVisible(False)
        
        # Initial deaktivieren
        self.set_item_controls_enabled(False)
        self.table_widget.itemSelectionChanged.connect(self.on_table_selection_changed)

        self.update_translations()

    def toggle_tag_panel(self):
        visible = self.tag_container.isVisible()
        self.tag_container.setVisible(not visible)
        self.btn_toggle_tags.setText(tr("hide_tags") if not visible else tr("show_tags"))

    def rebuild_tag_checkboxes(self):
        while self.tag_layout.count():
            item = self.tag_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.checkbox_map = {}
        self.tags_info = load_tags()
        columns = 4
        row = col = 0
        for code, desc in self.tags_info.items():
            cb = QCheckBox(f"{code}: {desc}")
            cb.setProperty("code", code)
            cb.stateChanged.connect(self.save_current_item_settings)
            self.tag_layout.addWidget(cb, row, col)
            self.checkbox_map[code] = cb
            col += 1
            if col >= columns:
                col = 0
                row += 1

    def setup_toolbar(self):
        style = QApplication.style()
        tb = self.toolbar

        act_add_files = QAction(style.standardIcon(QStyle.SP_FileIcon), tr("add_files"), self)
        act_add_files.setToolTip(tr("add_files"))
        act_add_files.triggered.connect(self.add_files_dialog)
        tb.addAction(act_add_files)

        act_add_folder = QAction(style.standardIcon(QStyle.SP_DirOpenIcon), tr("add_folder"), self)
        act_add_folder.setToolTip(tr("add_folder"))
        act_add_folder.triggered.connect(self.add_folder_dialog)
        tb.addAction(act_add_folder)

        act_preview = QAction(style.standardIcon(QStyle.SP_FileDialogDetailedView), tr("preview_rename"), self)
        act_preview.setToolTip(tr("preview_rename"))
        act_preview.triggered.connect(self.preview_rename)
        tb.addAction(act_preview)

        act_rename = QAction(style.standardIcon(QStyle.SP_DialogApplyButton), tr("rename_all"), self)
        act_rename.setToolTip(tr("rename_all"))
        act_rename.triggered.connect(self.direct_rename)
        tb.addAction(act_rename)

        act_clear = QAction(style.standardIcon(QStyle.SP_DialogResetButton), tr("clear_list"), self)
        act_clear.setToolTip(tr("clear_list"))
        act_clear.triggered.connect(self.clear_all)
        tb.addAction(act_clear)

        gear_icon = QIcon.fromTheme("preferences-system", style.standardIcon(QStyle.SP_FileDialogDetailedView))
        act_settings = QAction(gear_icon, tr("settings_title"), self)
        act_settings.setToolTip(tr("settings_title"))
        act_settings.triggered.connect(self.open_settings)
        tb.addAction(act_settings)

        tb.addSeparator()
        self.lbl_project = QLabel(tr("project_number_label"))
        self.input_project = QLineEdit()
        self.input_project.setInputMask("C000000;_")
        self.input_project.setText("C")
        self.input_project.setMaximumWidth(120)
        self.input_project.setPlaceholderText(tr("project_number_placeholder"))
        tb.addWidget(self.lbl_project)
        tb.addWidget(self.input_project)


    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec() == QDialog.Accepted:
            cfg = load_config()
            set_language(cfg.get("language", "en"))
            self.update_translations()
            self.rebuild_tag_checkboxes()

    def update_translations(self):
        self.setWindowTitle(tr("app_title"))
        actions = self.toolbar.actions()
        labels = [
            "add_files", "add_folder", "preview_rename",
            "rename_all", "clear_list", "settings_title"
        ]
        for action, key in zip(actions, labels):
            action.setText(tr(key))
            action.setToolTip(tr(key))
        # update form labels
        self.lbl_project.setText(tr("project_number_label"))
        self.input_project.setPlaceholderText(tr("project_number_placeholder"))
        if self.tag_container.isVisible():
            self.btn_toggle_tags.setText(tr("hide_tags"))
        else:
            self.btn_toggle_tags.setText(tr("show_tags"))

    def add_files_dialog(self):
        exts = " ".join(f"*{e}" for e in ItemSettings.ACCEPT_EXTENSIONS)
        filter_str = f"Images and Videos ({exts})"
        files, _ = QFileDialog.getOpenFileNames(
            self, tr("add_files"), "",
            filter_str
        )
        self.table_widget.add_paths(files)

    def add_folder_dialog(self):
        folder = QFileDialog.getExistingDirectory(self, tr("add_folder"))
        if folder:
            entries = os.listdir(folder)
            paths = [
                os.path.join(folder, name)
                for name in entries
                if os.path.isfile(os.path.join(folder, name)) and
                   os.path.splitext(name)[1].lower() in ItemSettings.ACCEPT_EXTENSIONS
            ]
            self.table_widget.add_paths(paths)

    def on_table_selection_changed(self):
        rows = [idx.row() for idx in self.table_widget.selectionModel().selectedRows()]
        if not rows:
            self.image_viewer.load_image("")
            self.zoom_slider.setValue(100)
            self.set_item_controls_enabled(False)
            self.table_widget.sync_check_column()
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


        intersect = set(settings_list[0].tags)
        union = set(settings_list[0].tags)
        for st in settings_list[1:]:
            intersect &= st.tags
            union |= st.tags
        for code, cb in self.checkbox_map.items():
            cb.blockSignals(True)
            if code in intersect:
                cb.setTristate(False)
                cb.setCheckState(Qt.Checked)
            elif code in union:
                cb.setTristate(True)
                cb.setCheckState(Qt.PartiallyChecked)
            else:
                cb.setTristate(False)
                cb.setCheckState(Qt.Unchecked)
            cb.blockSignals(False)

        self.load_preview(first.original_path)
        self.table_widget.sync_check_column()

    def save_current_item_settings(self):
        rows = [idx.row() for idx in self.table_widget.selectionModel().selectedRows()]
        if not rows:
            return
        checkbox_states = {code: cb.checkState() for code, cb in self.checkbox_map.items()}
        for row in rows:
            item0 = self.table_widget.item(row, 1)
            settings: ItemSettings = item0.data(ROLE_SETTINGS)
            if settings is None:
                continue
            for code, state in checkbox_states.items():
                if state == Qt.Checked:
                    settings.tags.add(code)
                elif state == Qt.Unchecked:
                    settings.tags.discard(code)
            tags_str = ",".join(sorted(settings.tags))
            cell_tags = self.table_widget.item(row, 2)
            cell_suffix = self.table_widget.item(row, 3)
            cell_tags.setText(tags_str)
            cell_tags.setToolTip(tags_str)
            cell_suffix.setText(settings.suffix)
            cell_suffix.setToolTip(settings.suffix)
            self.update_row_background(row, settings)
        self.table_widget.sync_check_column()

    def update_row_background(self, row: int, settings: ItemSettings):
        for col in range(4):
            item = self.table_widget.item(row, col)
            if settings and (settings.suffix or settings.tags):
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
        if col not in (2, 3):
            return
        item0 = self.table_widget.item(row, 1)
        if not item0:
            return
        settings: ItemSettings = item0.data(ROLE_SETTINGS)
        if settings is None:
            return
        if col == 2:
            raw_tags = {t.strip() for t in item.text().split(',') if t.strip()}
            valid_tags = {t for t in raw_tags if t in self.tags_info}
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
        elif col == 3:
            settings.suffix = item.text().strip()
            item.setToolTip(settings.suffix)
        self.update_row_background(row, settings)
        if row in {idx.row() for idx in self.table_widget.selectionModel().selectedRows()}:
            self.on_table_selection_changed()

    def load_preview(self, path: str):
        ext = os.path.splitext(path)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
            self.image_viewer.load_image(path)
            # initial Fit, behält Rotation intern
            self.image_viewer.zoom_fit()
            self.zoom_slider.setValue(self.image_viewer._zoom_pct)
        else:
            self.image_viewer.load_image("")
            self.zoom_slider.setValue(100)

    def on_zoom_slider_changed(self, value: int):
        self.image_viewer._zoom_pct = value
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
        for cb in self.checkbox_map.values():
            cb.setEnabled(enabled)

    def clear_all(self):
        self.table_widget.setRowCount(0)
        self.image_viewer.load_image("")
        self.zoom_slider.setValue(100)
        for cb in self.checkbox_map.values():
            cb.setChecked(False)
        self.set_item_controls_enabled(False)

    def build_rename_mapping(self):
        project = self.input_project.text().strip()
        if not re.fullmatch(r"C\d{6}", project):
            QMessageBox.warning(self, tr("missing_project"), tr("missing_project_msg"))
            return None
        n = self.table_widget.rowCount()
        if n == 0:
            QMessageBox.information(self, tr("no_files"), tr("no_files_msg"))
            return None
        self.save_current_item_settings()
        items = []
        for row in range(n):
            item0 = self.table_widget.item(row, 1)
            path = item0.data(Qt.UserRole)
            settings: ItemSettings = item0.data(ROLE_SETTINGS)
            if settings is None:
                settings = ItemSettings(path)
                item0.setData(ROLE_SETTINGS, settings)
            settings.original_path = path
            items.append(settings)
        renamer = Renamer(project, items)
        mapping = renamer.build_mapping()
        return mapping

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
        mapping = self.build_rename_mapping()
        if mapping is None:
            return
        reply = QMessageBox.question(
            self, tr("confirm_rename"),
            tr("confirm_rename_msg"),
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            table_mapping = []
            for settings, orig, new in mapping:
                new_name = os.path.basename(new)
                for row in range(self.table_widget.rowCount()):
                    item0 = self.table_widget.item(row, 1)
                    if item0.data(Qt.UserRole) == orig:
                        table_mapping.append((row, orig, new_name, new))
                        break
            self.execute_rename_with_progress(table_mapping)

    def execute_rename_with_progress(self, table_mapping):
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

