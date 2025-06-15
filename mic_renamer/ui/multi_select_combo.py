from PySide6.QtWidgets import QComboBox, QLineEdit
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt, Signal


class MultiSelectComboBox(QComboBox):
    selectionChanged = Signal()

    def __init__(self, options: dict[str, str], parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)
        self._model = QStandardItemModel()
        for code, desc in options.items():
            item = QStandardItem(f"{code}: {desc}")
            item.setData(code, Qt.UserRole)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self._model.appendRow(item)
        self.setModel(self._model)
        self.view().pressed.connect(self.handle_item_pressed)
        self.lineEdit().textEdited.connect(self.filter_items)
        self._selected = set()

    def handle_item_pressed(self, index):
        item = self._model.itemFromIndex(index)
        if item.checkState() == Qt.Checked:
            item.setCheckState(Qt.Unchecked)
            self._selected.discard(item.data(Qt.UserRole))
        else:
            item.setCheckState(Qt.Checked)
            self._selected.add(item.data(Qt.UserRole))
        self.update_display()
        self.selectionChanged.emit()
        # keep popup open
        self.showPopup()

    def filter_items(self, text: str):
        for row in range(self._model.rowCount()):
            item = self._model.item(row)
            match = text.lower() in item.text().lower()
            self.view().setRowHidden(row, not match)

    def update_display(self):
        self.lineEdit().setText(", ".join(sorted(self._selected)))

    def selected_codes(self) -> set[str]:
        return set(self._selected)

    def set_selected_codes(self, codes: set[str]):
        self._selected = set(codes)
        for row in range(self._model.rowCount()):
            item = self._model.item(row)
            code = item.data(Qt.UserRole)
            item.setCheckState(Qt.Checked if code in self._selected else Qt.Unchecked)
        self.update_display()
