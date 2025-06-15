from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from .ui.main_window import MainWindow


class Application:
    def __init__(self) -> None:
        try:
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
        except Exception:
            pass
        self.app = QApplication(sys.argv)

    def run(self) -> int:
        window = MainWindow()
        window.show()
        return self.app.exec()


def main() -> int:
    return Application().run()


if __name__ == "__main__":
    sys.exit(main())

