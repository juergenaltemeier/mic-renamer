import os
from PySide6.QtWidgets import (
    QWidget, QSplitter, QHBoxLayout, QVBoxLayout, QGridLayout,
    QPushButton, QSlider, QFileDialog, QMessageBox, QToolBar,
    QGraphicsView, QGraphicsScene, QStyle,
    QApplication, QLabel, QLineEdit,
    QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressDialog, QDialog, QDialogButtonBox, QAbstractItemView
)
from PySide6.QtGui import QPixmap, QPainter, QColor, QAction
from PySide6.QtCore import Qt

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
        # Setze Zoom und behalte Rotation
        self._zoom_pct = int(factor * 100)
        # Reset und anwenden
        self.resetTransform()
        if self._rotation != 0:
            self.rotate(self._rotation)
        self.scale(factor, factor)
        # Scrollbars zurücksetzen
        try:
            self.horizontalScrollBar().setValue(0)
            self.verticalScrollBar().setValue(0)
        except Exception:
            pass

class DragDropTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["Filename", "Tags", "Suffix"])
        header = self.horizontalHeader()
        # Erste Spalte interaktiv, zweite interaktiv, dritte füllt Rest
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setStretchLastSection(True)
        header.sectionDoubleClicked.connect(self.on_header_double_clicked)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setAcceptDrops(True)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        self.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.verticalHeader().setDefaultSectionSize(24)

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
                item = self.item(row, 0)
                if item and item.data(Qt.UserRole) == path:
                    duplicate = True
                    break
            if duplicate:
                continue
            row = self.rowCount()
            self.insertRow(row)
            fname_item = QTableWidgetItem(os.path.basename(path))
            fname_item.setData(Qt.UserRole, path)
            fname_item.setBackground(QColor(30, 30, 30))
            fname_item.setForeground(QColor(220, 220, 220))
            tags_item = QTableWidgetItem("")
            suffix_item = QTableWidgetItem("")
            tags_item.setToolTip("")    
            suffix_item.setToolTip("")
            self.setItem(row, 0, fname_item)
            self.setItem(row, 1, tags_item)
            self.setItem(row, 2, suffix_item)
        if self.rowCount() > 0 and not self.selectionModel().hasSelection():
            self.selectRow(0)

class RenamerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("app_title"))

        main_layout = QVBoxLayout(self)

        self.toolbar = QToolBar()
        self.setup_toolbar()
        main_layout.addWidget(self.toolbar)

        # container for project/suffix controls and selected file label
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        lbl_project = QLabel(tr("project_number_label"))
        self.input_project = QLineEdit()
        self.input_project.setPlaceholderText(tr("project_number_placeholder"))
        controls_layout.addWidget(lbl_project)
        controls_layout.addWidget(self.input_project)
        controls_layout.addSpacing(10)

        lbl_selected = QLabel(tr("selected_file_label"))
        self.label_selected_file = QLabel("<none>")
        self.label_selected_file.setWordWrap(True)
        controls_layout.addWidget(lbl_selected)
        controls_layout.addWidget(self.label_selected_file)
        controls_layout.addSpacing(5)

        lbl_suffix = QLabel(tr("custom_suffix_label"))
        self.input_item_suffix = QLineEdit()
        self.input_item_suffix.setPlaceholderText(tr("custom_suffix_placeholder"))
        controls_layout.addWidget(lbl_suffix)
        controls_layout.addWidget(self.input_item_suffix)
        self.input_item_suffix.editingFinished.connect(self.save_current_item_settings)
        controls_layout.addSpacing(10)

        main_layout.addWidget(controls_widget)

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
        viewer_layout.addWidget(self.image_viewer, 5)

        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(10)
        self.zoom_slider.setMaximum(500)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setTickInterval(10)
        self.zoom_slider.setTickPosition(QSlider.TicksBelow)
        self.zoom_slider.valueChanged.connect(self.on_zoom_slider_changed)
        viewer_layout.addWidget(self.zoom_slider)

        self.table_widget = DragDropTableWidget()

        grid.addWidget(viewer_widget, 0, 0)
        grid.addWidget(self.table_widget, 0, 1)

        # Tag container spanning both columns
        tag_container = QWidget()
        tag_main_layout = QVBoxLayout(tag_container)
        lbl_tags = QLabel(tr("select_tags_label"))
        tag_main_layout.addWidget(lbl_tags)
        checkbox_container = QWidget()
        tag_layout = QGridLayout(checkbox_container)
        tag_layout.setContentsMargins(0, 0, 0, 0)
        columns = 4
        row = col = 0
        self.tags_info = load_tags()
        self.checkbox_map = {}
        for code, desc in self.tags_info.items():
            cb = QCheckBox(f"{code}: {desc}")
            cb.setProperty("code", code)
            cb.stateChanged.connect(self.save_current_item_settings)
            tag_layout.addWidget(cb, row, col)
            self.checkbox_map[code] = cb
            col += 1
            if col >= columns:
                col = 0
                row += 1
        tag_main_layout.addWidget(checkbox_container)

        grid.addWidget(tag_container, 1, 0, 1, 2)

        # Initial deaktivieren
        self.set_item_controls_enabled(False)
        self.table_widget.currentCellChanged.connect(self.on_table_selection_changed)

        self.update_translations()

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

        act_settings = QAction(style.standardIcon(QStyle.SP_FileDialogInfoView), tr("settings_title"), self)
        act_settings.setToolTip(tr("settings_title"))
        act_settings.triggered.connect(self.open_settings)
        tb.addAction(act_settings)

    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec() == QDialog.Accepted:
            cfg = load_config()
            set_language(cfg.get("language", "en"))
            self.update_translations()
            self.tags_info = load_tags()
            # rebuild tag checkboxes maybe later

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
        self.input_project.setPlaceholderText(tr("project_number_placeholder"))
        self.input_item_suffix.setPlaceholderText(tr("custom_suffix_placeholder"))

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

    def on_table_selection_changed(self, row, col):
        if row < 0 or row >= self.table_widget.rowCount():
            self.label_selected_file.setText("<none>")
            self.image_viewer.load_image("")
            self.zoom_slider.setValue(100)
            self.set_item_controls_enabled(False)
            return

        self.set_item_controls_enabled(True)
        item0 = self.table_widget.item(row, 0)
        path = item0.data(Qt.UserRole)
        self.label_selected_file.setText(os.path.basename(path))
        settings: ItemSettings = item0.data(ROLE_SETTINGS)
        if settings is None:
            settings = ItemSettings(path)
            item0.setData(ROLE_SETTINGS, settings)

        self.input_item_suffix.blockSignals(True)
        self.input_item_suffix.setText(settings.suffix)
        self.input_item_suffix.blockSignals(False)
        for code, cb in self.checkbox_map.items():
            cb.blockSignals(True)
            cb.setChecked(code in settings.tags)
            cb.blockSignals(False)

        # Preview laden mit Fit
        self.load_preview(path)
        self.update_row_background(row, settings)

    def save_current_item_settings(self):
        row = self.table_widget.currentRow()
        if row < 0:
            return
        item0 = self.table_widget.item(row, 0)
        settings: ItemSettings = item0.data(ROLE_SETTINGS)
        if not settings:
            return
        settings.suffix = self.input_item_suffix.text().strip()
        selected = {code for code, cb in self.checkbox_map.items() if cb.isChecked()}
        settings.tags = selected
        tags_str = ",".join(sorted(settings.tags))
        cell_tags = self.table_widget.item(row, 1)
        cell_suffix = self.table_widget.item(row, 2)
        cell_tags.setText(tags_str)
        cell_tags.setToolTip(tags_str)
        cell_suffix.setText(settings.suffix)
        cell_suffix.setToolTip(settings.suffix)
        self.update_row_background(row, settings)

    def update_row_background(self, row: int, settings: ItemSettings):
        for col in range(3):
            item = self.table_widget.item(row, col)
            if settings and (settings.suffix or settings.tags):
                item.setBackground(QColor('#335533'))
                item.setForeground(QColor('#ffffff'))
            else:
                item.setBackground(QColor(30, 30, 30))
                item.setForeground(QColor(220, 220, 220))

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
        self.input_item_suffix.setEnabled(enabled)
        for cb in self.checkbox_map.values():
            cb.setEnabled(enabled)

    def clear_all(self):
        self.table_widget.setRowCount(0)
        self.label_selected_file.setText("<none>")
        self.image_viewer.load_image("")
        self.zoom_slider.setValue(100)
        self.input_item_suffix.setText("")
        for cb in self.checkbox_map.values():
            cb.setChecked(False)
        self.set_item_controls_enabled(False)

    def build_rename_mapping(self):
        project = self.input_project.text().strip()
        if not project:
            QMessageBox.warning(self, tr("missing_project"), tr("missing_project_msg"))
            return None
        n = self.table_widget.rowCount()
        if n == 0:
            QMessageBox.information(self, tr("no_files"), tr("no_files_msg"))
            return None
        self.save_current_item_settings()
        items = []
        for row in range(n):
            item0 = self.table_widget.item(row, 0)
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
                item0 = self.table_widget.item(row, 0)
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
                    item0 = self.table_widget.item(row, 0)
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
                    item0 = self.table_widget.item(row, 0)
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

