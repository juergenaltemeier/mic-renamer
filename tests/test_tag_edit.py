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
    table.selectionModel().select(
        index, QItemSelectionModel.Select | QItemSelectionModel.Rows
    )


def test_edit_tags_updates_selected(app, monkeypatch, tmp_path):
    monkeypatch.setattr(
        "mic_renamer.logic.tag_loader.load_tags", lambda: {"T": "Test"}
    )
    monkeypatch.setattr(
        "mic_renamer.ui.panels.file_table.load_tags", lambda: {"T": "Test"}
    )
    img1 = tmp_path / "one.jpg"
    img2 = tmp_path / "two.jpg"
    img1.write_bytes(b"x")
    img2.write_bytes(b"y")
    win = RenamerApp()
    win.table_widget.add_paths([str(img1), str(img2)])
    select_two_rows(win.table_widget)
    win.table_widget._selection_before_edit = [0, 1]
    win.table_widget.item(0, 2).setText("T")
    assert win.table_widget.item(0, 2).text() == "T"
    assert win.table_widget.item(1, 2).text() == "T"
    settings1 = win.table_widget.item(0, 1).data(ROLE_SETTINGS)
    settings2 = win.table_widget.item(1, 1).data(ROLE_SETTINGS)
    assert settings1.tags == {"T"}
    assert settings2.tags == {"T"}


def test_existing_tags_unchanged(app, monkeypatch, tmp_path):
    monkeypatch.setattr(
        "mic_renamer.logic.tag_loader.load_tags", lambda: {"T": "Test", "X": "X"}
    )
    monkeypatch.setattr(
        "mic_renamer.ui.panels.file_table.load_tags", lambda: {"T": "Test", "X": "X"}
    )
    img1 = tmp_path / "one.jpg"
    img2 = tmp_path / "two.jpg"
    img1.write_bytes(b"x")
    img2.write_bytes(b"y")
    win = RenamerApp()
    win.table_widget.add_paths([str(img1), str(img2)])
    win.table_widget.item(1, 2).setText("X")
    select_two_rows(win.table_widget)
    win.table_widget._selection_before_edit = [0, 1]
    win.table_widget.item(0, 2).setText("T")
    assert win.table_widget.item(0, 2).text() == "T"
    assert win.table_widget.item(1, 2).text() == "X"
    settings1 = win.table_widget.item(0, 1).data(ROLE_SETTINGS)
    settings2 = win.table_widget.item(1, 1).data(ROLE_SETTINGS)
    assert settings1.tags == {"T"}
    assert settings2.tags == {"X"}
