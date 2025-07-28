"""
This module defines the `ModeTabs` widget, which provides a tabbed interface
for different file renaming modes. Each tab contains a `DragDropTableWidget`
configured for a specific renaming mode (Normal, Position, PA_MAT).
"""
import logging

from PySide6.QtWidgets import QTabWidget, QWidget, QVBoxLayout
from .file_table import DragDropTableWidget
from ...utils.i18n import tr

logger = logging.getLogger(__name__)


class ModeTabs(QWidget):
    """
    A tabbed widget that organizes different file renaming modes.

    Each tab hosts a `DragDropTableWidget` instance, allowing users to switch
    between different renaming workflows (Normal, Position, PA_MAT).
    """

    def __init__(self, parent: QWidget | None = None):
        """
        Initializes the ModeTabs widget.

        Args:
            parent (QWidget | None): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        logger.info("ModeTabs widget initialized.")
        
        self.layout = QVBoxLayout(self) # Main vertical layout for the widget.
        self.tabs = QTabWidget() # Create the QTabWidget.
        self.layout.addWidget(self.tabs) # Add the tab widget to the layout.

        # Create a DragDropTableWidget for each renaming mode.
        self.normal_tab = DragDropTableWidget() # Table for "normal" mode.
        self.position_tab = DragDropTableWidget() # Table for "position" mode.
        self.pa_mat_tab = DragDropTableWidget() # Table for "pa_mat" mode.

        # Add each table as a new tab, using translated names for tab titles.
        self.tabs.addTab(self.normal_tab, tr("mode_normal"))
        self.tabs.addTab(self.position_tab, tr("mode_position"))
        self.tabs.addTab(self.pa_mat_tab, tr("mode_pa_mat"))
        logger.debug("Tabs added for Normal, Position, and PA_MAT modes.")

        # Set the specific mode for each table. This will configure their headers and behavior.
        self.normal_tab.set_mode("normal")
        self.position_tab.set_mode("position")
        self.pa_mat_tab.set_mode("pa_mat")
        logger.debug("Modes set for individual table widgets.")

    def current_table(self) -> DragDropTableWidget:
        """
        Returns the currently active `DragDropTableWidget` (the table in the selected tab).

        Returns:
            DragDropTableWidget: The table widget of the currently selected tab.
        """
        # QTabWidget.currentWidget() returns the widget displayed in the currently selected tab.
        current_widget = self.tabs.currentWidget()
        if isinstance(current_widget, DragDropTableWidget):
            return current_widget
        else:
            # This case should ideally not happen if only DragDropTableWidget instances are added.
            logger.error(f"Current widget is not a DragDropTableWidget: {type(current_widget)}. Returning normal_tab as fallback.")
            return self.normal_tab # Fallback to normal_tab in unexpected cases.

    def all_tables(self) -> list[DragDropTableWidget]:
        """
        Returns a list of all `DragDropTableWidget` instances managed by this `ModeTabs` widget.

        Returns:
            list[DragDropTableWidget]: A list containing all table widgets.
        """
        return [self.normal_tab, self.position_tab, self.pa_mat_tab]
