import os
import json
import pytest
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt

from mic_renamer.ui.main_window import RenamerApp
from mic_renamer.logic.settings import ItemSettings
from mic_renamer import config_manager

@pytest.fixture
def app(qtbot):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    test_app = QApplication.instance()
    if test_app is None:
        test_app = QApplication([])
    
    window = RenamerApp()
    qtbot.addWidget(window)
    return window

def test_session_save_and_restore(app: RenamerApp, tmp_path, monkeypatch):
    # 1. Setup initial state
    img_a = tmp_path / "a.jpg"
    img_b = tmp_path / "b.jpg"
    img_a.write_bytes(b"x")
    img_b.write_bytes(b"y")

    app.table_widget.add_paths([str(img_a), str(img_b)])
    app.input_project.setText("C123456")

    # Modify settings for one of the items
    settings_a = app.table_widget.item(0, 1).data(Qt.UserRole)
    settings_a.tags = {"tag1", "tag2"}
    settings_a.suffix = "suffix1"
    app.table_widget.item(0, 2).setText(",".join(sorted(settings_a.tags)))
    app.table_widget.item(0, 4).setText(settings_a.suffix)

    # 2. Save the session
    app.save_session()

    # 3. Create a new window to simulate app restart
    new_window = RenamerApp()

    # 4. Mock the QMessageBox to automatically say "Yes" to restore
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Yes)

    # 5. Restore the session in the new window
    new_window.restore_session()

    # 6. Assert the state is restored
    assert new_window.input_project.text() == "C123456"
    assert new_window.table_widget.rowCount() == 2
    
    # Check item A's settings
    restored_settings_a = new_window.table_widget.item(0, 1).data(Qt.UserRole)
    assert restored_settings_a.tags == {"tag1", "tag2"}
    assert restored_settings_a.suffix == "suffix1"
    
    # Check item B's settings (should be default)
    restored_settings_b = new_window.table_widget.item(1, 1).data(Qt.UserRole)
    assert restored_settings_b.tags == set()
    assert restored_settings_b.suffix == ""

    # 7. Ensure the session file is deleted after restore
    session_file = os.path.join(config_manager.config_dir, "session.json")
    assert not os.path.exists(session_file)
