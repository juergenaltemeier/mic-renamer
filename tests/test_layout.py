import os
import pytest
from PySide6.QtWidgets import QApplication

from mic_renamer.ui.main_window import RenamerApp


@pytest.fixture(scope="module")
def app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_splitter_below_toolbar(app):
    win = RenamerApp()
    win.show()
    app.processEvents()
    layout = win.layout()
    margins = layout.contentsMargins()
    assert (margins.left(), margins.top(), margins.right(), margins.bottom()) == (0, 0, 0, 0)
    assert layout.spacing() == 2
    assert layout.itemAt(0).widget() is win.toolbar
    assert layout.itemAt(1).widget() is win.splitter
    win.close()
