import os
import pytest
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, QThread

from mic_renamer.ui.main_window import RenamerApp


@pytest.fixture(scope="module")
def app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    a = QApplication.instance()
    if a is None:
        a = QApplication([])
    return a


class DummyProgress:
    """Minimal progress dialog replacement for tests."""
    def __init__(self, *args, **kwargs):
        self.canceled = type("Signal", (), {"connect": lambda *a, **k: None})()

    def setWindowModality(self, *_):
        pass

    def setMinimumDuration(self, *_):
        pass

    def setValue(self, *_):
        pass

    def close(self):
        pass

    def wasCanceled(self):
        return False


def test_rename_updates_sorted_rows(app, monkeypatch, tmp_path):
    img_a = tmp_path / "a.jpg"
    img_b = tmp_path / "b.jpg"
    img_a.write_bytes(b"x")
    img_b.write_bytes(b"y")

    win = RenamerApp()
    win.table_widget.add_paths([str(img_a), str(img_b)])
    # sort descending by filename
    win.table_widget.sortByColumn(1, Qt.DescendingOrder)
    win.table_widget.setSortingEnabled(True)
    app.processEvents()

    new_c = tmp_path / "c.jpg"
    new_d = tmp_path / "d.jpg"

    table_mapping = [
        (0, str(img_b), new_c.name, str(new_c)),
        (1, str(img_a), new_d.name, str(new_d)),
    ]

    monkeypatch.setattr("mic_renamer.ui.main_window.QProgressDialog", DummyProgress)
    monkeypatch.setattr(QThread, "start", lambda self: self.started.emit())
    monkeypatch.setattr(QThread, "quit", lambda self: None)
    monkeypatch.setattr(QThread, "wait", lambda self: None)
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)

    win.execute_rename_with_progress(table_mapping)
    app.processEvents()

    # sorting should still be descending
    assert win.table_widget.horizontalHeader().sortIndicatorOrder() == Qt.DescendingOrder
    assert win.table_widget.item(0, 1).text() == "d.jpg"
    assert win.table_widget.item(1, 1).text() == "c.jpg"
    assert os.path.exists(new_c)
    assert os.path.exists(new_d)
    win.close()

