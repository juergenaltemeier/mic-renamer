# main.py

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from .ui.main_window import RenamerApp

if __name__ == '__main__':
    try:
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
    except Exception:
        pass
    app = QApplication(sys.argv)
    window = RenamerApp()
    window.setMinimumSize(1200, 800)
    window.resize(1200, 800)
    window.show()
    sys.exit(app.exec())

