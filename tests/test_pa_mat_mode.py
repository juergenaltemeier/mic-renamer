import os
import pytest
from PySide6.QtWidgets import QApplication

from mic_renamer.ui.main_window import RenamerApp, ROLE_SETTINGS, MODE_PA_MAT
from mic_renamer.logic.settings import ItemSettings
from mic_renamer.logic.renamer import Renamer


@pytest.fixture(scope="module")
def app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_pa_mat_column_stored(app, tmp_path):
    img = tmp_path / "img.jpg"
    img.write_bytes(b"x")
    win = RenamerApp()
    idx = win.combo_mode.findData(MODE_PA_MAT)
    win.combo_mode.setCurrentIndex(idx)
    win.table_widget.add_paths([str(img)])
    win.table_widget.item(0, 2).setText("42")
    settings = win.table_widget.item(0, 1).data(ROLE_SETTINGS)
    assert settings.pa_mat == "42"


def test_pa_mat_used_in_name(tmp_path):
    f = tmp_path / "a.jpg"
    f.write_bytes(b"x")
    item = ItemSettings(str(f))
    item.pa_mat = "7"
    renamer = Renamer("C000001", [item], mode=MODE_PA_MAT)
    mapping = renamer.build_mapping()
    assert len(mapping) == 1
    _, _, new = mapping[0]
    assert "_pa_mat7" in os.path.basename(new)
