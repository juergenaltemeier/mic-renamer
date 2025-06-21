import os
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QItemSelectionModel

from mic_renamer.ui.main_window import RenamerApp, ROLE_SETTINGS


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


def test_clear_selected_suffixes(app, tmp_path):
    img1 = tmp_path / "one.jpg"
    img2 = tmp_path / "two.jpg"
    img1.write_bytes(b"x")
    img2.write_bytes(b"y")
    win = RenamerApp()
    win.table_widget.add_paths([str(img1), str(img2)])
    win.table_widget.item(0, 4).setText("foo")
    win.table_widget.item(1, 4).setText("bar")
    select_two_rows(win.table_widget)
    win.clear_selected_suffixes()
    assert win.table_widget.item(0, 4).text() == ""
    assert win.table_widget.item(1, 4).text() == ""
    st0 = win.table_widget.item(0, 1).data(ROLE_SETTINGS)
    st1 = win.table_widget.item(1, 1).data(ROLE_SETTINGS)
    assert st0.suffix == ""
    assert st1.suffix == ""
