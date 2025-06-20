import os
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QItemSelectionModel

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


def test_edit_suffix_updates_selected(app, tmp_path):
    img1 = tmp_path / "one.jpg"
    img2 = tmp_path / "two.jpg"
    img1.write_bytes(b"x")
    img2.write_bytes(b"y")
    win = RenamerApp()
    win.table_widget.add_paths([str(img1), str(img2)])
    select_two_rows(win.table_widget)
    win.table_widget._selection_before_edit = [0, 1]
    win.table_widget.item(0, 4).setText("foo")
    assert win.table_widget.item(0, 4).text() == "foo"
    assert win.table_widget.item(1, 4).text() == "foo"


def test_existing_suffix_unchanged(app, tmp_path):
    img1 = tmp_path / "one.jpg"
    img2 = tmp_path / "two.jpg"
    img1.write_bytes(b"x")
    img2.write_bytes(b"y")
    win = RenamerApp()
    win.table_widget.add_paths([str(img1), str(img2)])
    win.table_widget.item(1, 4).setText("bar")
    select_two_rows(win.table_widget)
    win.table_widget._selection_before_edit = [0, 1]
    win.table_widget.item(0, 4).setText("foo")
    assert win.table_widget.item(0, 4).text() == "foo"
    assert win.table_widget.item(1, 4).text() == "bar"
