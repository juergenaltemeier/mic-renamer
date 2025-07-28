"""
This module defines the `HelpDialog` class, a PyQt/PySide dialog that displays
help content to the user. The content is loaded from translation resources
and displayed as rich text, supporting basic HTML formatting.
"""
# -*- coding: utf-8 -*-
import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
)

from mic_renamer.utils.i18n import tr as _ # Alias tr for convenience in translations

logger = logging.getLogger(__name__)


class HelpDialog(QDialog):
    """
    A dialog window that displays help information for the application.

    The content is loaded from the application's translation resources and
    can include rich text (HTML) formatting.
    """

    def __init__(self, parent=None):
        """
        Initializes the HelpDialog.

        Args:
            parent (QWidget, optional): The parent widget for this dialog. Defaults to None.
        """
        super().__init__(parent)
        self.setWindowTitle(_("help_title")) # Set the window title using a translated string.
        self.setMinimumSize(600, 400) # Set a reasonable minimum size for the dialog.
        logger.info("HelpDialog initialized.")

        layout = QVBoxLayout(self) # Create a vertical layout for the dialog content.
        self.setLayout(layout) # Set the layout for the dialog.

        # QLabel to display the help content.
        text_label = QLabel(_("help_content_html")) # Load HTML content from translations.
        text_label.setWordWrap(True) # Enable word wrapping for long text.
        text_label.setTextFormat(Qt.RichText) # Interpret the text as rich text (HTML).
        text_label.setOpenExternalLinks(True) # Allow opening external links from the HTML.
        layout.addWidget(text_label) # Add the text label to the layout.
        logger.debug("Help content label added.")

        # Standard OK button box.
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept) # Connect the OK button to the dialog's accept slot.
        layout.addWidget(button_box) # Add the button box to the layout.
        logger.debug("Dialog button box added.")

        # Set size policy to expanding to allow the dialog to grow.
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
