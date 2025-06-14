from PySide6.QtWidgets import QDialog, QTableWidget, QTableWidgetItem, QVBoxLayout, QDialogButtonBox
from PySide6.QtCore import Qt
import os
from ..utils.i18n import tr

def show_preview(parent, mapping: list[tuple]):
    dlg = QDialog(parent)
    dlg.setWindowTitle(tr("preview_rename"))
    layout = QVBoxLayout(dlg)
    table = QTableWidget(len(mapping), 2)
    table.setHorizontalHeaderLabels([
        tr("current_name"),
        tr("proposed_new_name")
    ])
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.setSelectionMode(QTableWidget.NoSelection)
    table.setFocusPolicy(Qt.NoFocus)
    for row, (item_setting, orig_path, new_path) in enumerate(mapping):
        table.setItem(row, 0, QTableWidgetItem(os.path.basename(orig_path)))
        table.setItem(row, 1, QTableWidgetItem(os.path.basename(new_path)))
    table.resizeColumnsToContents()
    table.resizeRowsToContents()
    table.setMinimumWidth(600)
    layout.addWidget(table)
    btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    layout.addWidget(btns)
    btns.accepted.connect(dlg.accept)
    btns.rejected.connect(dlg.reject)
    return dlg.exec() == QDialog.Accepted

