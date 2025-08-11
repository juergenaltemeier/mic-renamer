"""
Application Bootstrapper for Mic-Renamer.

This module is the main entry point for the application. It handles the
initial setup of configuration, logging, and the Qt application itself.
It creates the main window, applies styling, and manages the application's
lifecycle.
"""

import logging
import os
import sys
import sys
from datetime import datetime
from importlib import resources
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from . import config_manager
from .ui.main_window import RenamerApp
from .ui.theme import apply_styles
from .utils.state_manager import StateManager


class Application:
    """
    The main application class.

    This class encapsulates the entire application, from initialization to
    execution and shutdown. It sets up logging, configuration, the main
    window, and the overall application state.
    """

    def __init__(self):
        """
        Initializes the Application instance.

        This involves:
        - Ensuring configuration files exist.
        - Setting up a robust logging system with log rotation.
        - Creating the QApplication instance with high DPI support.
        - Applying the user-selected theme.
        - Setting the application icon.
        - Initializing the state manager and the main window.
        - Restoring the window's previous size, position, and state.
        """
        # Ensure essential configuration files and directories are present.
        config_manager.ensure_files()

        # Set up logging infrastructure.
        self._configure_logging()

        self.logger = logging.getLogger(__name__)
        self.logger.info("Mic-Renamer application starting...")

        # Create and configure the core Qt application object.
        self.app = self._create_qt_application()

        # Load and apply the visual theme from settings.
        self._apply_theme()

        # Set the application's window icon.
        self._set_window_icon()

        # Initialize the application state manager.
        self.state = StateManager(config_manager.config_dir)

        # Create and configure the main application window.
        self.window = self._create_main_window()

        # Install the global exception handler.
        self._install_exception_hook()

    def _install_exception_hook(self):
        """
        Installs a global exception hook to catch unhandled exceptions.
        """
        sys.excepthook = self._handle_exception

    def _handle_exception(self, exc_type, exc_value, exc_traceback):
        """
        Handles unhandled exceptions, logs them, and shows a critical error message.
        """
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        self.logger.critical("Unhandled exception caught:", exc_info=(exc_type, exc_value, exc_traceback))

        error_message = (
            "An unexpected error occurred and the application must close.\n\n"
            f"Details of the error have been logged to:\n{self.logger.handlers[0].baseFilename}"
        )
        QMessageBox.critical(None, "Application Error", error_message)
        self.app.quit()

    def _configure_logging(self):
        """
        Configures the logging system, including log rotation.

        Logs are stored in a 'logs' subdirectory within the user's
        configuration directory. A new log file is created for each session.
        To prevent excessive disk usage, old log files are automatically
        purged, keeping only the 10 most recent logs.
        """
        try:
            log_dir = Path(config_manager.config_dir) / "logs"
            log_dir.mkdir(exist_ok=True)

            # Clean up old log files, keeping the last 10.
            log_files = sorted(
                log_dir.glob("*.log"), key=os.path.getmtime, reverse=True
            )
            for old_log in log_files[9:]:
                try:
                    old_log.unlink()
                except OSError as e:
                    logging.warning(f"Failed to remove old log file: {old_log}. Error: {e}")

            # Define the path for the current session's log file.
            log_file = log_dir / f"session-{datetime.now():%Y-%m-%d_%H-%M-%S}.log"

            # Configure the root logger.
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                handlers=[
                    logging.FileHandler(log_file),
                    logging.StreamHandler(sys.stdout)
                ],
            )
        except (OSError, IOError) as e:
            # Fallback to basic console logging if file logging fails.
            logging.basicConfig(level=logging.WARNING)
            logging.critical(f"Failed to configure file-based logging: {e}")


    def _create_qt_application(self) -> QApplication:
        """
        Creates and configures the QApplication instance.

        Enables high DPI scaling for better visuals on modern displays.
        """
        try:
            # These attributes should be set before the QApplication is instantiated.
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
        except Exception as e:
            logging.warning(f"Could not set high DPI attributes: {e}")

        return QApplication(sys.argv)

    def _apply_theme(self):
        """
        Loads the theme from config and applies it to the application.

        """
        theme = config_manager.get("theme", "dark")
        try:
            apply_styles(self.app, theme)
            self.logger.info(f"Applied '{theme}' theme.")
        except Exception as e:
            self.logger.error(f"Failed to apply theme '{theme}': {e}")
            # Fallback to a default state if styling fails
            apply_styles(self.app, "dark")


    def _set_window_icon(self):
        """
        Sets the main application window icon.

        The icon is loaded from the embedded resources.
        """
        try:
            logo_path_obj = resources.files("mic_renamer") / "favicon.png"
            if logo_path_obj.is_file():
                icon = QIcon(str(logo_path_obj))
                self.app.setWindowIcon(icon)
            else:
                self.logger.warning("Application icon 'favicon.png' not found.")
        except Exception as e:
            self.logger.error(f"Failed to load window icon: {e}")


    def _create_main_window(self) -> RenamerApp:
        """
        Creates, configures, and positions the main application window.

        Restores window size and position from the previous session if
        available, otherwise uses default values from the configuration.
        The window is centered on the primary screen on first launch.
        """
        window = RenamerApp(state_manager=self.state)

        # Set the window icon (for the window itself, not just the app).
        if self.app.windowIcon():
            window.setWindowIcon(self.app.windowIcon())

        # Configure minimum and initial window size from config/state.
        min_w = config_manager.get("window_min_width", 1200)
        min_h = config_manager.get("window_min_height", 800)
        window.setMinimumSize(min_w, min_h)

        width = self.state.get("width", config_manager.get("window_width", 1200))
        height = self.state.get("height", config_manager.get("window_height", 800))
        window.resize(width, height)

        # Center the window on the primary display for a better user experience.
        try:
            screen = self.app.primaryScreen()
            if screen:
                geom = screen.availableGeometry()
                x = geom.x() + (geom.width() - window.width()) // 2
                y = geom.y() + (geom.height() - window.height()) // 2
                window.move(x, y)
        except Exception as e:
            self.logger.error(f"Could not center the main window: {e}")


        # Restore the splitter sizes from the previous session.
        sizes = self.state.get("splitter_sizes")
        if sizes:
            window.set_splitter_sizes(sizes)

        return window

    def run(self) -> int:
        """
        Starts the Qt event loop and shows the main window.

        Returns:
            int: The exit code of the application.
        """
        self.logger.info("Showing main window.")
        self.window.show()
        self.window._check_and_offer_certificate_install() # Call after showing window
        try:
            result = self.app.exec()
            self.logger.info("Application finished with exit code %d.", result)
            return result
        except Exception as e:
            self.logger.critical(f"Application crashed with an unhandled exception: {e}", exc_info=True)
            # In case of a crash, return a non-zero exit code.
            return 1