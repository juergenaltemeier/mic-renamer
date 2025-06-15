import os
import pytest
from PySide6.QtWidgets import QApplication, QLabel, QCheckBox

from mic_renamer.ui.panels.tag_panel import TagPanel


@pytest.fixture(scope="module")
def app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_rebuild_with_none(monkeypatch, app):
    monkeypatch.setattr("mic_renamer.ui.panels.tag_panel.load_tags", lambda: None)
    panel = TagPanel()
    assert panel.tags_info == {}
    assert panel.tag_layout.count() == 1
    widget = panel.tag_layout.itemAt(0).widget()
    assert isinstance(widget, QLabel)


def test_rebuild_with_empty(monkeypatch, app):
    monkeypatch.setattr("mic_renamer.ui.panels.tag_panel.load_tags", lambda: {})
    panel = TagPanel()
    assert panel.tags_info == {}
    assert panel.tag_layout.count() == 1
    widget = panel.tag_layout.itemAt(0).widget()
    assert isinstance(widget, QLabel)


def test_rebuild_with_tags(monkeypatch, app):
    monkeypatch.setattr(
        "mic_renamer.ui.panels.tag_panel.load_tags",
        lambda: {"A": "Alpha", "B": "Beta"},
    )
    panel = TagPanel()
    assert set(panel.tags_info.keys()) == {"A", "B"}
    checkboxes = [
        panel.tag_layout.itemAt(i).widget()
        for i in range(panel.tag_layout.count())
        if isinstance(panel.tag_layout.itemAt(i).widget(), QCheckBox)
    ]
    assert len(checkboxes) == 2
