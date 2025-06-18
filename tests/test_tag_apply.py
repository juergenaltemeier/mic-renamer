import os
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from mic_renamer.ui.main_window import RenamerApp, ROLE_SETTINGS


@pytest.fixture(scope="module")
def app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_checkbox_applies_tag(app, tmp_path):
    img = tmp_path / "test.jpg"
    img.write_bytes(b"x")
    win = RenamerApp()
    win.table_widget.add_paths([str(img)])
    win.table_widget.selectRow(0)
    code = next(iter(win.tag_panel.checkbox_map))
    win.on_tag_toggled(code, Qt.Checked)
    cell_text = win.table_widget.item(0, 2).text()
    assert cell_text == code
    item0 = win.table_widget.item(0, 1)
    settings = item0.data(ROLE_SETTINGS)
    assert code in settings.tags


def test_existing_tags_detected(app, monkeypatch, tmp_path):
    tags = {"A": "Alpha", "B": "Beta"}
    monkeypatch.setattr(
        "mic_renamer.logic.tag_loader.load_tags",
        lambda: tags,
    )
    monkeypatch.setattr(
        "mic_renamer.ui.panels.file_table.load_tags",
        lambda: tags,
    )
    img = tmp_path / "image_A_B.jpg"
    img.write_bytes(b"x")
    win = RenamerApp()
    win.table_widget.add_paths([str(img)])
    win.table_widget.selectRow(0)
    cell_text = win.table_widget.item(0, 2).text()
    assert cell_text == "A,B"
    item0 = win.table_widget.item(0, 1)
    settings = item0.data(ROLE_SETTINGS)
    assert settings.tags == {"A", "B"}
    win.on_table_selection_changed()
    assert win.tag_panel.checkbox_map["A"].checkState() == Qt.Checked
    assert win.tag_panel.checkbox_map["B"].checkState() == Qt.Checked
