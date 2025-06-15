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


def test_checkbox_applies_tag(app):
    win = RenamerApp()
    win.table_widget.add_paths(["/tmp/test.jpg"])
    win.table_widget.selectRow(0)
    code = next(iter(win.tag_panel.checkbox_map))
    win.on_tag_toggled(code, Qt.Checked)
    cell_text = win.table_widget.item(0, 2).text()
    assert cell_text == code
    item0 = win.table_widget.item(0, 1)
    settings = item0.data(ROLE_SETTINGS)
    assert code in settings.tags
