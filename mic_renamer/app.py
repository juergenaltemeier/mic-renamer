"""Application bootstrapper."""
import logging
import os
from datetime import datetime
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
import sys
from importlib import resources

from .ui.main_window import RenamerApp
from .ui.theme import apply_dark_theme
from .utils.state_manager import StateManager
from . import config_manager


class Application:
    """Main application class."""

    def __init__(self):
        # create config files on first run
        config_manager.ensure_files()
        
        # Configure logging
        log_dir = os.path.join(config_manager.config_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        # Rotate logs, keeping the last 10
        log_files = sorted(
            [os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.endswith(".log")],
            key=os.path.getmtime,
            reverse=True
        )
        for old_log in log_files[9:]:
            try:
                os.remove(old_log)
            except OSError as e:
                logging.warning(f"Failed to remove old log file: {e}")

        log_file = os.path.join(log_dir, f"session-{datetime.now():%Y-%m-%d_%H-%M-%S}.log")
        
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Application starting...")
        try:
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
        except Exception:
            pass
        self.app = QApplication(sys.argv)
        apply_dark_theme(self.app)
        logo = resources.files("mic_renamer") / "favicon.png"
        if logo.is_file():
            icon = QIcon(str(logo))
            self.app.setWindowIcon(icon)
        
        self.state = StateManager(config_manager.config_dir)
        self.window = RenamerApp(state_manager=self.state)
        if logo.is_file():
            self.window.setWindowIcon(icon)
        min_w = config_manager.get("window_min_width", 1200)
        min_h = config_manager.get("window_min_height", 800)
        self.window.setMinimumSize(min_w, min_h)
        width = self.state.get("width", config_manager.get("window_width", 1200))
        height = self.state.get("height", config_manager.get("window_height", 800))
        self.window.resize(width, height)
        sizes = self.state.get("splitter_sizes")
        if sizes:
            self.window.set_splitter_sizes(sizes)

    def run(self) -> int:
        """Start the Qt event loop."""
        self.logger.info("Showing main window.")
        self.window.show()
        result = self.app.exec()
        self.logger.info("Application finished with exit code %d.", result)
        return result
