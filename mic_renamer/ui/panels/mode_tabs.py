from PySide6.QtWidgets import QTabWidget, QWidget, QVBoxLayout
from .file_table import DragDropTableWidget
from ...utils.i18n import tr

class ModeTabs(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        self.normal_tab = DragDropTableWidget()
        self.position_tab = DragDropTableWidget()
        self.pa_mat_tab = DragDropTableWidget()

        self.tabs.addTab(self.normal_tab, tr("mode_normal"))
        self.tabs.addTab(self.position_tab, tr("mode_position"))
        self.tabs.addTab(self.pa_mat_tab, tr("mode_pa_mat"))

        self.normal_tab.set_mode("normal")
        self.position_tab.set_mode("position")
        self.pa_mat_tab.set_mode("pa_mat")
    
    def current_table(self):
        return self.tabs.currentWidget()
