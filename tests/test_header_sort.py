import os
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest

from mic_renamer.ui.main_window import RenamerApp


@pytest.fixture(scope="module")
def app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_header_sorting(app, tmp_path):
    img1 = tmp_path / "b.jpg"
    img2 = tmp_path / "a.jpg"
    img1.write_bytes(b"x")
    img2.write_bytes(b"y")
    win = RenamerApp()
    win.table_widget.add_paths([str(img1), str(img2)])
    assert win.table_widget.item(0, 1).text() == "a.jpg"
    assert win.table_widget.item(1, 1).text() == "b.jpg"

    header = win.table_widget.horizontalHeader()
    x = header.sectionPosition(1) + header.sectionSize(1) // 2
    pos = QPoint(x, header.height() // 2)
    QTest.mouseClick(header.viewport(), Qt.LeftButton, pos=pos)
    app.processEvents()

    assert win.table_widget.item(0, 1).text() == "b.jpg"
    assert win.table_widget.item(1, 1).text() == "a.jpg"
