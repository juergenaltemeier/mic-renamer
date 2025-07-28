"""
This module defines the `RenameOptionsDialog` class, a PyQt/PySide dialog that allows
users to configure options for the renaming process. These options include selecting
the destination directory for renamed files and choosing whether to compress images
after renaming.
"""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from .. import config_manager
from ..utils.i18n import tr

logger = logging.getLogger(__name__)


class RenameOptionsDialog(QDialog):
    """
    A dialog for selecting rename options, such as the output directory and post-rename compression.

    This dialog provides radio buttons for choosing between original directories or a custom
    save directory, and a checkbox for enabling/disabling image compression after renaming.
    """

    def __init__(self, parent=None):
        """
        Initializes the RenameOptionsDialog.

        Args:
            parent (QWidget, optional): The parent widget for this dialog. Defaults to None.
        """
        super().__init__(parent)
        self.setWindowTitle(tr("rename_options_title")) # Set dialog title from translations.
        logger.info("RenameOptionsDialog initialized.")
        self._setup_ui() # Set up the user interface.

    def _setup_ui(self) -> None:
        """
        Sets up the user interface of the dialog.

        This method organizes the layout into sections for directory options,
        compression options, and standard dialog buttons.
        """
        layout = QVBoxLayout(self) # Main vertical layout for the dialog.
        
        self._setup_directory_options(layout) # Add directory selection radio buttons and input.
        self._setup_compression_option(layout) # Add compression checkbox.
        self._setup_buttons(layout) # Add OK/Cancel buttons.
        logger.debug("RenameOptionsDialog UI setup complete.")

    def _setup_directory_options(self, layout: QVBoxLayout) -> None:
        """
        Sets up the radio buttons and input field for selecting the destination directory.

        Users can choose to save files in their original directories or specify a custom folder.

        Args:
            layout (QVBoxLayout): The main layout to which these options will be added.
        """
        # Radio button for using original directories.
        self.radio_orig = QRadioButton(tr("use_original_directory"))
        self.radio_orig.setChecked(True) # Set as default selected option.
        layout.addWidget(self.radio_orig)

        # Radio button for specifying a custom save directory.
        self.radio_custom = QRadioButton(tr("default_save_dir_label"))
        layout.addWidget(self.radio_custom)

        # Horizontal layout for the custom directory input field and browse button.
        dir_layout = QHBoxLayout()
        # QLineEdit to display and allow editing of the custom directory path.
        self.edit_dir = QLineEdit(config_manager.get("default_save_directory", ""))
        btn_browse = QPushButton("...") # Button to open a file dialog for choosing a directory.
        btn_browse.clicked.connect(self._choose_dir) # Connect browse button to its handler.
        dir_layout.addWidget(self.edit_dir)
        dir_layout.addWidget(btn_browse)
        layout.addLayout(dir_layout)
        logger.debug("Directory options setup complete.")

    def _setup_compression_option(self, layout: QVBoxLayout) -> None:
        """
        Sets up the checkbox for enabling/disabling post-rename image compression.

        Args:
            layout (QVBoxLayout): The main layout to which this option will be added.
        """
        # Checkbox for compressing images after renaming.
        self.chk_compress = QCheckBox(tr("compress_after_rename"))
        # Set initial checked state based on saved configuration.
        self.chk_compress.setChecked(config_manager.get("compress_after_rename", False))
        layout.addWidget(self.chk_compress)
        logger.debug("Compression option setup complete.")

    def _setup_buttons(self, layout: QVBoxLayout) -> None:
        """
        Sets up the standard OK and Cancel buttons for the dialog.

        Args:
            layout (QVBoxLayout): The main layout to which these buttons will be added.
        """
        # Create standard OK and Cancel buttons.
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept) # Connect OK button to dialog's accept slot.
        btns.rejected.connect(self.reject) # Connect Cancel button to dialog's reject slot.
        layout.addWidget(btns)
        logger.debug("Dialog buttons setup complete.")

    def _choose_dir(self) -> None:
        """
        Opens a QFileDialog to allow the user to select a custom directory.

        If a directory is selected, its path is set to the `edit_dir` QLineEdit,
        and the `radio_custom` option is automatically selected.
        """
        # Open a directory selection dialog, starting in the currently displayed path.
        path = QFileDialog.getExistingDirectory(
            self, tr("default_save_dir_label"), self.edit_dir.text()
        )
        if path:
            self.edit_dir.setText(path) # Update the QLineEdit with the selected path.
            self.radio_custom.setChecked(True) # Automatically select the custom radio button.
            logger.info(f"Custom save directory selected: {path}")
        else:
            logger.debug("Directory selection canceled.")

    @property
    def directory(self) -> Path | None:
        """
        Returns the selected destination directory as a Path object.

        If the "Use original directory" option is selected, returns None.
        If a custom directory is selected but the path is empty, also returns None.

        Returns:
            Path | None: The selected directory path, or None if original directory
                         is chosen or custom path is empty.
        """
        if self.radio_orig.isChecked():
            logger.debug("Selected directory: Original (None)")
            return None
        
        path_str = self.edit_dir.text().strip()
        if path_str:
            selected_path = Path(path_str)
            logger.debug(f"Selected directory: {selected_path}")
            return selected_path
        else:
            logger.warning("Custom directory selected but path is empty. Returning None.")
            return None

    @property
    def compress_after(self) -> bool:
        """
        Returns whether the user has opted to compress files after renaming.

        Returns:
            bool: True if the compression checkbox is checked, False otherwise.
        """
        is_checked = self.chk_compress.isChecked()
        logger.debug(f"Compress after rename: {is_checked}")
        return is_checked


