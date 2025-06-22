import os
import pytest
from PySide6.QtWidgets import QApplication

from mic_renamer.ui.main_window import RenamerApp, ROLE_SETTINGS


@pytest.fixture(scope="module")
def app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_suffix_detected(app, monkeypatch, tmp_path):
    tags = {"A": "Alpha"}
    monkeypatch.setattr("mic_renamer.logic.tag_loader.load_tags", lambda: tags)
    monkeypatch.setattr("mic_renamer.ui.panels.file_table.load_tags", lambda: tags)
    img = tmp_path / "proj_A_230101_extra.jpg"
    img.write_bytes(b"x")
    win = RenamerApp()
    win.table_widget.add_paths([str(img)])
    cell_text = win.table_widget.item(0, 4).text()
    assert cell_text == "extra"
    item0 = win.table_widget.item(0, 1)
    settings = item0.data(ROLE_SETTINGS)
    assert settings.suffix == "extra"


def test_suffix_not_extracted_for_numeric_or_tag(app, monkeypatch, tmp_path):
    tags = {"B": "Beta"}
    monkeypatch.setattr("mic_renamer.logic.tag_loader.load_tags", lambda: tags)
    monkeypatch.setattr("mic_renamer.ui.panels.file_table.load_tags", lambda: tags)
    img1 = tmp_path / "img_B_230101_001.jpg"
    img2 = tmp_path / "img_B_230101_B.jpg"
    img1.write_bytes(b"x")
    img2.write_bytes(b"y")
    win = RenamerApp()
    win.table_widget.add_paths([str(img1), str(img2)])
    assert win.table_widget.item(0, 4).text() == ""
    assert win.table_widget.item(1, 4).text() == ""
    item0 = win.table_widget.item(0, 1)
    item1 = win.table_widget.item(1, 1)
    settings0 = item0.data(ROLE_SETTINGS)
    settings1 = item1.data(ROLE_SETTINGS)
    assert settings0.suffix == ""
    assert settings1.suffix == ""


def test_suffix_before_numeric_index(app, monkeypatch, tmp_path):
    tags = {"A": "Alpha"}
    monkeypatch.setattr("mic_renamer.logic.tag_loader.load_tags", lambda: tags)
    monkeypatch.setattr("mic_renamer.ui.panels.file_table.load_tags", lambda: tags)
    img = tmp_path / "C123456_A_240101_note_001.jpg"
    img.write_bytes(b"x")
    win = RenamerApp()
    win.table_widget.add_paths([str(img)])
    assert win.table_widget.item(0, 4).text() == "note"
