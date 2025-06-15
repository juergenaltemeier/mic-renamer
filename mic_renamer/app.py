"""Application bootstrapper."""
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
import sys

from .ui.main_window import RenamerApp
from .utils.state_manager import StateManager
from . import config_manager


class Application:
    """Main application class."""

    def __init__(self):
        try:
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
        except Exception:
            pass
        self.app = QApplication(sys.argv)
        self.state = StateManager(config_manager.config_dir)
        self.window = RenamerApp(state_manager=self.state)
        min_w = config_manager.get("window_min_width", 1200)
        min_h = config_manager.get("window_min_height", 800)
        self.window.setMinimumSize(min_w, min_h)
        width = self.state.get("width", config_manager.get("window_width", 1200))
        height = self.state.get("height", config_manager.get("window_height", 800))
        self.window.resize(width, height)

    def run(self) -> int:
        """Start the Qt event loop."""
        self.window.show()
        return self.app.exec()
