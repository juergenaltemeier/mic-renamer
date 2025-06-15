from PySide6.QtWidgets import QApplication


def apply_theme(app: QApplication, theme: dict):
    """Apply basic theme colors to the QApplication."""
    if not theme:
        return
    style_sheet = f"""
    QToolBar {{ background-color: {theme['primary_blue']}; }}
    QToolBar QToolButton {{ color: white; }}
    QWidget#MainPanel {{ background-color: {theme['background_white']}; }}
    QTableWidget {{ background-color: {theme['background_white']}; selection-background-color: #ADD8E6; }}
    """
    app.setStyleSheet(style_sheet)
