import os
import pytest
from PySide6.QtWidgets import QApplication, QSizePolicy


from mic_renamer.ui.main_window import RenamerApp
from mic_renamer.ui.constants import DEFAULT_MARGIN, DEFAULT_SPACING


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
    assert (
        margins.left(),
        margins.top(),
        margins.right(),
        margins.bottom(),
    ) == (
        DEFAULT_MARGIN,
        DEFAULT_MARGIN,
        DEFAULT_MARGIN,
        DEFAULT_MARGIN,
    )
    assert layout.spacing() == DEFAULT_SPACING
    assert layout.itemAt(0).widget() is win.toolbar
    assert layout.itemAt(1).widget() is win.splitter
    assert layout.stretch(1) == 1
    policy = win.toolbar.sizePolicy()
    assert policy.verticalPolicy() == QSizePolicy.Fixed
    win.close()
