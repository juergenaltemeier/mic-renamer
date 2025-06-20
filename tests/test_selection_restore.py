import os
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QItemSelectionModel
from PySide6.QtTest import QTest

from mic_renamer.ui.main_window import RenamerApp


@pytest.fixture(scope="module")
def app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def select_two_rows(table):
    table.selectRow(0)
    index = table.model().index(1, 0)
    table.selectionModel().select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)


def test_selection_restored_after_edit(app, tmp_path):
    img1 = tmp_path / "one.jpg"
    img2 = tmp_path / "two.jpg"
    img1.write_bytes(b"x")
    img2.write_bytes(b"y")
    win = RenamerApp()
    win.table_widget.add_paths([str(img1), str(img2)])
    select_two_rows(win.table_widget)
    assert {i.row() for i in win.table_widget.selectionModel().selectedRows()} == {0, 1}
    index = win.table_widget.model().index(0, 4)
    rect = win.table_widget.visualRect(index)
    QTest.mouseClick(win.table_widget.viewport(), Qt.LeftButton, pos=rect.center())
    app.processEvents()
    win.table_widget.item(0, 4).setText("foo")
    rows = {i.row() for i in win.table_widget.selectionModel().selectedRows()}
    assert rows == {0, 1}
