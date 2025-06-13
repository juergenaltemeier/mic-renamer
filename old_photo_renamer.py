
import sys
import os
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QWidget, QListWidget, QListWidgetItem, QCheckBox, QPushButton,
    QLineEdit, QLabel, QHBoxLayout, QVBoxLayout, QScrollArea,
    QMessageBox, QFileDialog, QDialog, QTableWidget, QTableWidgetItem,
    QDialogButtonBox, QProgressDialog, QStyle
)
from PySide6.QtCore import Qt

# === Konfiguration: Tags und Beschreibungen ===
TAGS_INFO = {
    "AU": "Autoclave Unit",
    "VC": "Valve Controller",
    "CU": "Control Unit",
    "HS": "Heat Sensor",
    "FU": "Filter Unit",
    # Weitere hinzufügen...
}

ACCEPT_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.mp4', '.avi', '.mov', '.mkv']
ROLE_SETTINGS = Qt.UserRole + 1

class DragDropListWidget(QListWidget):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setMinimumWidth(300)

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
            added_any = False
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if os.path.isfile(path):
                    ext = os.path.splitext(path)[1].lower()
                    if ext in ACCEPT_EXTENSIONS:
                        exists = False
                        for i in range(self.count()):
                            if self.item(i).data(Qt.UserRole) == path:
                                exists = True; break
                        if not exists:
                            item = QListWidgetItem(os.path.basename(path))
                            item.setData(Qt.UserRole, path)
                            settings = {"tags": set(), "suffix": ""}
                            item.setData(ROLE_SETTINGS, settings)
                            self.addItem(item)
                            added_any = True
            if added_any:
                if self.currentItem() is None and self.count() > 0:
                    self.setCurrentRow(0)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

class RenamerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Photo/Video Renamer")

        main_layout = QHBoxLayout(self)

        self.list_widget = DragDropListWidget()
        main_layout.addWidget(self.list_widget, 1)
        self.list_widget.currentItemChanged.connect(self.on_item_selected)

        controls = QWidget()
        controls_layout = QVBoxLayout(controls)

        # Global: Projekt-Nummer
        lbl_project = QLabel("Project Number:")
        self.input_project = QLineEdit()
        self.input_project.setPlaceholderText("z.B. C230105")
        controls_layout.addWidget(lbl_project)
        controls_layout.addWidget(self.input_project)
        controls_layout.addSpacing(10)

        # Ausgewählte Datei
        lbl_selected = QLabel("Selected File:")
        self.label_selected_file = QLabel("<none>")
        self.label_selected_file.setWordWrap(True)
        controls_layout.addWidget(lbl_selected)
        controls_layout.addWidget(self.label_selected_file)
        controls_layout.addSpacing(5)

        # Per-Item: Suffix
        lbl_item_suffix = QLabel("Custom Suffix for this file:")
        self.input_item_suffix = QLineEdit()
        self.input_item_suffix.setPlaceholderText("z.B. DSC00138")
        controls_layout.addWidget(lbl_item_suffix)
        controls_layout.addWidget(self.input_item_suffix)
        self.input_item_suffix.editingFinished.connect(self.save_current_item_settings)
        controls_layout.addSpacing(10)

        # Per-Item: Tags
        lbl_tags = QLabel("Select Tags for this file:")
        controls_layout.addWidget(lbl_tags)
        tag_container = QWidget()
        tag_layout = QVBoxLayout(tag_container)
        self.checkbox_map = {}
        for code, desc in TAGS_INFO.items():
            cb = QCheckBox(f"{code}: {desc}")
            cb.setProperty("code", code)
            cb.stateChanged.connect(self.save_current_item_settings)
            tag_layout.addWidget(cb)
            self.checkbox_map[code] = cb
        tag_layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tag_container)
        scroll.setFixedHeight(150)
        controls_layout.addWidget(scroll)
        controls_layout.addSpacing(10)

        # Buttons: Add Files, Add Folder, Preview & Direct Rename side by side, Clear
        btn_add = QPushButton("Add Files...")
        btn_add.clicked.connect(self.add_files_dialog)
        controls_layout.addWidget(btn_add)

        btn_add_folder = QPushButton("Add Folder...")
        icon_folder = QApplication.style().standardIcon(QStyle.SP_DirOpenIcon)
        btn_add_folder.setIcon(icon_folder)
        btn_add_folder.clicked.connect(self.add_folder_dialog)
        controls_layout.addWidget(btn_add_folder)

        # Horizontal layout for preview and direct rename
        hbtn_layout = QHBoxLayout()
        style = QApplication.style()
        # Preview button with icon
        btn_preview = QPushButton("Preview Rename")
        icon_preview = style.standardIcon(QStyle.SP_FileDialogDetailedView)
        btn_preview.setIcon(icon_preview)
        btn_preview.clicked.connect(self.preview_rename)
        hbtn_layout.addWidget(btn_preview)

        # Direct rename button with icon
        btn_direct = QPushButton("Rename All")
        icon_direct = style.standardIcon(QStyle.SP_DialogApplyButton)
        btn_direct.setIcon(icon_direct)
        btn_direct.clicked.connect(self.direct_rename)
        hbtn_layout.addWidget(btn_direct)

        controls_layout.addLayout(hbtn_layout)

        btn_clear = QPushButton("Clear List")
        controls_layout.addWidget(btn_clear)
        btn_clear.clicked.connect(self.clear_all)

        controls_layout.addStretch()
        main_layout.addWidget(controls, 1)

        self.set_item_controls_enabled(False)

    def add_files_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Files", "",
            "Images and Videos (*.jpg *.jpeg *.png *.gif *.bmp *.mp4 *.avi *.mov *.mkv)"
        )
        self._add_paths(files)

    def add_folder_dialog(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            # Non-recursive: nur Dateien im Ordner
            entries = os.listdir(folder)
            paths = []
            for name in entries:
                path = os.path.join(folder, name)
                if os.path.isfile(path):
                    ext = os.path.splitext(path)[1].lower()
                    if ext in ACCEPT_EXTENSIONS:
                        paths.append(path)
            self._add_paths(paths)

    def _add_paths(self, paths):
        added_any = False
        for path in paths:
            if os.path.isfile(path):
                ext = os.path.splitext(path)[1].lower()
                if ext in ACCEPT_EXTENSIONS:
                    exists = False
                    for i in range(self.list_widget.count()):
                        if self.list_widget.item(i).data(Qt.UserRole) == path:
                            exists = True; break
                    if not exists:
                        item = QListWidgetItem(os.path.basename(path))
                        item.setData(Qt.UserRole, path)
                        settings = {"tags": set(), "suffix": ""}
                        item.setData(ROLE_SETTINGS, settings)
                        self.list_widget.addItem(item)
                        added_any = True
        if added_any:
            if self.list_widget.currentItem() is None and self.list_widget.count() > 0:
                self.list_widget.setCurrentRow(0)

    def on_item_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        if previous is not None:
            self.save_settings_for_item(previous)
        if current is None:
            self.label_selected_file.setText("<none>")
            self.input_item_suffix.setText("")
            for cb in self.checkbox_map.values():
                cb.setChecked(False)
            self.set_item_controls_enabled(False)
            return
        self.set_item_controls_enabled(True)
        file_path = current.data(Qt.UserRole)
        self.label_selected_file.setText(os.path.basename(file_path))
        settings = current.data(ROLE_SETTINGS)
        if settings is None:
            settings = {"tags": set(), "suffix": ""}
            current.setData(ROLE_SETTINGS, settings)
        self.input_item_suffix.blockSignals(True)
        self.input_item_suffix.setText(settings.get("suffix", ""))
        self.input_item_suffix.blockSignals(False)
        for code, cb in self.checkbox_map.items():
            cb.blockSignals(True)
            cb.setChecked(code in settings.get("tags", set()))
            cb.blockSignals(False)

    def set_item_controls_enabled(self, enabled: bool):
        self.input_item_suffix.setEnabled(enabled)
        for cb in self.checkbox_map.values():
            cb.setEnabled(enabled)

    def save_current_item_settings(self):
        item = self.list_widget.currentItem()
        if item:
            self.save_settings_for_item(item)

    def save_settings_for_item(self, item: QListWidgetItem):
        settings = item.data(ROLE_SETTINGS) or {"tags": set(), "suffix": ""}
        suffix = self.input_item_suffix.text().strip()
        settings["suffix"] = suffix
        selected = set()
        for code, cb in self.checkbox_map.items():
            if cb.isChecked():
                selected.add(code)
        settings["tags"] = selected
        item.setData(ROLE_SETTINGS, settings)

    def clear_all(self):
        self.list_widget.clear()
        self.on_item_selected(None, None)

    def build_rename_mapping(self):
        project = self.input_project.text().strip()
        if not project:
            QMessageBox.warning(self, "Missing Project Number", "Bitte Projekt-Nummer eingeben.")
            return None
        if self.list_widget.count() == 0:
            QMessageBox.information(self, "No Files", "Keine Dateien in der Liste zum Umbenennen.")
            return None
        self.save_current_item_settings()
        date_str = datetime.now().strftime("%y%m%d")
        mapping = []
        count = 1
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            orig_path = item.data(Qt.UserRole)
            settings = item.data(ROLE_SETTINGS) or {"tags": set(), "suffix": ""}
            ordered_codes = [code for code in TAGS_INFO.keys() if code in settings.get("tags", set())]
            suffix = settings.get("suffix", "").strip()
            dirpath = os.path.dirname(orig_path)
            ext = os.path.splitext(orig_path)[1]
            parts = [project] + ordered_codes + [date_str, f"{count:03d}"]
            basename = "_".join(parts)
            if suffix:
                basename += "_" + suffix
            new_name = basename + ext
            new_path = os.path.join(dirpath, new_name)
            temp_count = count
            temp_parts = parts.copy()
            temp_new_path = new_path
            # Vermeide Kollision, ignoriere gleichen Pfad
            while os.path.exists(temp_new_path) and os.path.abspath(orig_path) != os.path.abspath(temp_new_path):
                temp_count += 1
                temp_parts[-1] = f"{temp_count:03d}"
                basename2 = "_".join(temp_parts)
                if suffix:
                    basename2 += "_" + suffix
                temp_new_path = os.path.join(dirpath, basename2 + ext)
            mapping.append((item, orig_path, os.path.basename(temp_new_path), temp_new_path))
            count += 1
        return mapping

    def preview_rename(self):
        mapping = self.build_rename_mapping()
        if mapping is None:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Preview Rename")
        dlg_layout = QVBoxLayout(dlg)
        table = QTableWidget(len(mapping), 2, dlg)
        table.setHorizontalHeaderLabels(["Current Name", "Proposed New Name"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.setFocusPolicy(Qt.NoFocus)
        for row, (item, orig_path, new_name, new_path) in enumerate(mapping):
            it1 = QTableWidgetItem(os.path.basename(orig_path))
            it2 = QTableWidgetItem(new_name)
            table.setItem(row, 0, it1)
            table.setItem(row, 1, it2)
        table.resizeColumnsToContents()
        table.resizeRowsToContents()
        table.setMinimumWidth(600)
        dlg_layout.addWidget(table)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=dlg)
        dlg_layout.addWidget(btns)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        if dlg.exec() == QDialog.Accepted:
            self.execute_rename_with_progress(mapping)

    def direct_rename(self):
        mapping = self.build_rename_mapping()
        if mapping is None:
            return
        reply = QMessageBox.question(
            self, "Confirm Rename",
            "Willst du wirklich direkt umbenennen ohne Vorschau?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            # Führe Umbenennen aus und zeige Fortschritt, aber Nachricht differenziert
            self.execute_rename_with_progress(mapping)

    def execute_rename_with_progress(self, mapping):
        total = len(mapping)
        progress = QProgressDialog("Renaming files...", "Abort", 0, total, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(200)
        progress.setValue(0)
        count_done = 0
        for idx, (item, orig_path, new_name, new_path) in enumerate(mapping):
            if progress.wasCanceled():
                break
            try:
                orig_abs = os.path.abspath(orig_path)
                new_abs = os.path.abspath(new_path)
                if orig_abs != new_abs:
                    os.rename(orig_path, new_path)
                    item.setText(os.path.basename(new_path))
                    item.setData(Qt.UserRole, new_path)
            except Exception as e:
                QMessageBox.warning(
                    self, "Rename Failed",
                    f"Fehler beim Umbenennen:\n{orig_path}\n→\n{new_path}\nError: {e}"
                )
            count_done += 1
            progress.setValue(count_done)
        progress.close()
        if progress.wasCanceled():
            QMessageBox.information(self, "Partial Rename", f"Umbenennen abgebrochen. {count_done} von {total} Dateien wurden umbenannt.")
        else:
            QMessageBox.information(self, "Done", "Alle Dateien wurden umbenannt.")

if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    window = RenamerApp()
    window.resize(1000, 600)
    window.show()
    sys.exit(app.exec())
