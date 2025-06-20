import os
import pytest
from PySide6.QtWidgets import QApplication
from mic_renamer.ui.main_window import RenamerApp


class DummyState:
    def __init__(self):
        self.data = {}
    def get(self, key, default=None):
        return self.data.get(key, default)
    def set(self, key, value):
        self.data[key] = value
    def save(self):
        pass


@pytest.fixture(scope="module")
def app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_splitter_state_persist(app):
    state = DummyState()
    win = RenamerApp(state_manager=state)
    win.show()
    app.processEvents()

    win.splitter.setSizes([100, 200])
    app.processEvents()
    sizes = win.splitter.sizes()

    win.close()
    assert state.data["splitter_sizes"] == sizes

    win2 = RenamerApp(state_manager=state)
    win2.show()
    app.processEvents()
    assert win2.splitter.sizes() == sizes
    win2.close()
