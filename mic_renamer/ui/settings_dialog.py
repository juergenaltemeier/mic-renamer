"""
This module defines the `SettingsDialog` class, a PyQt/PySide dialog for managing
various application settings. It provides a user-friendly interface to configure
general options, compression settings, and manage custom tags.
"""
from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import requests
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .. import config_manager
from ..logic.tag_loader import (
    DEFAULT_TAGS_FILE,
    load_tags,
    load_tags_multilang,
    restore_default_tags as restore_tags_to_default_file, # Alias to avoid name conflict
)
from ..logic.tag_usage import reset_counts
from ..utils.i18n import tr
from .panels.compression_settings import CompressionSettingsPanel

# Type checking for StateManager to avoid circular imports if needed
if TYPE_CHECKING:
    from ..utils.state_manager import StateManager

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """
    A dialog for configuring various application settings.

    This dialog provides tabs for different categories of settings, including
    general options (extensions, directories, language, theme, toolbar style, tags)
    and compression settings. It allows users to modify, save, and restore default
    application preferences.
    """

    def __init__(self, parent: QWidget | None = None, state_manager: 'StateManager' | None = None):
        """
        Initializes the SettingsDialog.

        Args:
            parent (QWidget | None): The parent widget for this dialog. Defaults to None.
            state_manager (StateManager | None): An optional StateManager instance for
                                                 persisting dialog size and position. Defaults to None.
        """
        super().__init__(parent)
        self.state_manager = state_manager
        self.setWindowTitle(tr("settings_title")) # Set dialog title from translations.
        # Load a copy of the current configuration to allow changes without affecting live config until accepted.
        self.cfg = config_manager.load().copy()
        logger.info("SettingsDialog initialized.")

        self._setup_ui() # Build the UI components.
        self._load_state() # Load dialog size/position from state manager.

    def _setup_ui(self) -> None:
        """
        Sets up the user interface of the dialog.

        This method creates a tabbed interface for organizing different setting categories:
        General settings and Compression settings.
        """
        layout = QVBoxLayout(self) # Main vertical layout for the dialog.
        tabs = QTabWidget() # Tab widget to organize settings.
        layout.addWidget(tabs)

        # Create and add the General settings tab.
        general_tab = self._create_general_tab()
        tabs.addTab(general_tab, tr("settings_title"))

        # Create and add the Compression settings panel (which is a QWidget).
        self.compression_panel = CompressionSettingsPanel(self.cfg) # Pass the config copy.
        tabs.addTab(self.compression_panel, tr("compression_settings"))

        self._setup_buttons(layout) # Add OK, Cancel, and Reset buttons.
        logger.debug("SettingsDialog UI setup complete.")

    def _create_general_tab(self) -> QWidget:
        """
        Creates and populates the "General" settings tab.

        This tab includes options for configuration path display, accepted file extensions,
        default save directory, language selection, theme selection, toolbar style, and tag management.

        Returns:
            QWidget: The configured general settings tab widget.
        """
        general = QWidget() # Create a new QWidget for the tab content.
        gen_layout = QVBoxLayout(general) # Vertical layout for this tab.

        self._add_config_path_label(gen_layout)
        self._add_accepted_extensions_input(gen_layout)
        self._add_save_directory_input(gen_layout)
        self._add_language_selection(gen_layout)
        self._add_theme_selection(gen_layout)
        self._add_toolbar_style_option(gen_layout)
        self._add_tags_table(gen_layout)

        logger.debug("General settings tab created.")
        return general

    def _add_config_path_label(self, layout: QVBoxLayout) -> None:
        """
        Adds a QLabel displaying the application's configuration directory path.

        Args:
            layout (QVBoxLayout): The layout to which the label will be added.
        """
        # Display the configuration directory path and set a tooltip.
        lbl_cfg = QLabel(f"{tr('config_path_label')}: {config_manager.config_dir}")
        lbl_cfg.setToolTip(tr('config_path_desc'))
        layout.addWidget(lbl_cfg)
        logger.debug("Config path label added.")

    def _add_accepted_extensions_input(self, layout: QVBoxLayout) -> None:
        """
        Adds an input field for managing accepted file extensions.

        Args:
            layout (QVBoxLayout): The layout to which the input will be added.
        """
        layout.addWidget(QLabel(tr("accepted_ext_label"))) # Label for the input field.
        # QLineEdit pre-populated with current accepted extensions, joined by ", ".
        self.edit_ext = QLineEdit(", ".join(self.cfg.get("accepted_extensions", [])))
        self.edit_ext.setToolTip(tr("accepted_ext_desc")) # Tooltip for user guidance.
        layout.addWidget(self.edit_ext)
        logger.debug("Accepted extensions input added.")

    def _add_save_directory_input(self, layout: QVBoxLayout) -> None:
        """
        Adds an input field and browse button for setting the default save directory.

        Args:
            layout (QVBoxLayout): The layout to which the input will be added.
        """
        hl_save = QHBoxLayout() # Horizontal layout for label, line edit, and button.
        lbl_save = QLabel(tr('default_save_dir_label'))
        lbl_save.setToolTip(tr('default_save_dir_desc'))
        hl_save.addWidget(lbl_save)
        # QLineEdit pre-populated with the current default save directory.
        self.edit_save_dir = QLineEdit(self.cfg.get('default_save_directory', ''))
        self.edit_save_dir.setToolTip(tr('default_save_dir_desc'))
        btn_browse_save = QPushButton('...') # Browse button.
        btn_browse_save.clicked.connect(self._choose_save_dir) # Connect to directory chooser.
        hl_save.addWidget(self.edit_save_dir)
        hl_save.addWidget(btn_browse_save)
        layout.addLayout(hl_save)
        logger.debug("Save directory input added.")

    def _add_language_selection(self, layout: QVBoxLayout) -> None:
        """
        Adds a QComboBox for selecting the application language.

        Args:
            layout (QVBoxLayout): The layout to which the combobox will be added.
        """
        hl = QHBoxLayout() # Horizontal layout for label and combobox.
        lbl_lang = QLabel(tr("language_label"))
        lbl_lang.setToolTip(tr("language_desc"))
        hl.addWidget(lbl_lang)
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["en", "de"]) # Add supported languages.
        self.combo_lang.setToolTip(tr("language_desc"))
        current_lang = self.cfg.get("language", "en")
        self.combo_lang.setCurrentText(current_lang) # Set current language based on config.
        hl.addWidget(self.combo_lang)
        layout.addLayout(hl)
        logger.debug("Language selection added.")

    def _add_theme_selection(self, layout: QVBoxLayout) -> None:
        """
        Adds a QComboBox for selecting the application theme (dark/light).

        Args:
            layout (QVBoxLayout): The layout to which the combobox will be added.
        """
        hl_theme = QHBoxLayout() # Horizontal layout for label and combobox.
        lbl_theme = QLabel(tr("theme_label"))
        lbl_theme.setToolTip(tr("theme_desc"))
        hl_theme.addWidget(lbl_theme)
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["dark", "light"]) # Add supported themes.
        self.combo_theme.setToolTip(tr("theme_desc"))
        current_theme = self.cfg.get("theme", "dark")
        self.combo_theme.setCurrentText(current_theme) # Set current theme based on config.
        hl_theme.addWidget(self.combo_theme)
        layout.addLayout(hl_theme)
        logger.debug("Theme selection added.")

    def _add_toolbar_style_option(self, layout: QVBoxLayout) -> None:
        """
        Adds a QCheckBox for toggling between icon-only and text-beside-icon toolbar styles.

        Args:
            layout (QVBoxLayout): The layout to which the checkbox will be added.
        """
        self.chk_toolbar_text = QCheckBox(tr("use_text_menu"))
        self.chk_toolbar_text.setToolTip(tr("use_text_menu_desc"))
        # Set checked state based on the 'toolbar_style' config value.
        self.chk_toolbar_text.setChecked(
            self.cfg.get("toolbar_style", "icons") == "text"
        )
        layout.addWidget(self.chk_toolbar_text)
        logger.debug("Toolbar style option added.")

    def _add_tags_table(self, layout: QVBoxLayout) -> None:
        """
        Adds a QTableWidget for managing custom tags, along with add/remove buttons.

        Users can view, add, and remove custom tags and their descriptions.

        Args:
            layout (QVBoxLayout): The layout to which the table and buttons will be added.
        """
        layout.addWidget(QLabel(tr("tags_label"))) # Label for the tags table.
        current_lang = self.cfg.get("language", "en")
        tags = load_tags_multilang() # Load all tags, including multi-language descriptions.
        
        # Filter tags to only show the current language's description for editing
        # For display, we show the code and the description for the current language.
        display_tags = {}
        for code, value in tags.items():
            if isinstance(value, dict):
                display_tags[code] = value.get(current_lang, next(iter(value.values()), ""))
            else:
                display_tags[code] = value

        self.tbl_tags = QTableWidget(len(display_tags), 2) # 2 columns: Code, Description.
        self.tbl_tags.setHorizontalHeaderLabels(["Code", "Description"]) # Header labels.
        
        # Populate the table with tag data.
        for row, (code, desc) in enumerate(display_tags.items()):
            self.tbl_tags.setItem(row, 0, QTableWidgetItem(code))
            self.tbl_tags.setItem(row, 1, QTableWidgetItem(desc))
        
        self.tbl_tags.horizontalHeader().setStretchLastSection(True) # Make last column stretch.
        layout.addWidget(self.tbl_tags)

        # Horizontal layout for Add/Remove tag buttons.
        hl_buttons = QHBoxLayout()
        btn_add = QPushButton("+")
        btn_add.setToolTip("Add new tag")
        btn_add.clicked.connect(self._add_tag_row) # Connect to add row method.
        hl_buttons.addWidget(btn_add)
        btn_remove = QPushButton("-")
        btn_remove.setToolTip("Remove selected tag")
        btn_remove.clicked.connect(self._remove_selected_tag_row) # Connect to remove row method.
        hl_buttons.addWidget(btn_remove)
        hl_buttons.addStretch() # Push buttons to the left.

        btn_update_tags = QPushButton(tr("update_tags_from_github"))
        btn_update_tags.setToolTip(tr("update_tags_from_github_desc"))
        btn_update_tags.clicked.connect(self._update_tags_from_github)
        hl_buttons.addWidget(btn_update_tags)

        layout.addLayout(hl_buttons)
        logger.debug("Tags table and controls added.")

    def _setup_buttons(self, layout: QVBoxLayout) -> None:
        """
        Sets up the dialog's main action buttons: OK, Cancel, Restore Defaults, and Reset Tag Usage.

        Args:
            layout (QVBoxLayout): The main layout to which these buttons will be added.
        """
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel) # Standard OK/Cancel.
        
        # Restore Defaults button.
        btn_restore = QPushButton(tr("restore_defaults"))
        btns.addButton(btn_restore, QDialogButtonBox.ResetRole) # Assign ResetRole.
        btn_restore.clicked.connect(self.restore_defaults) # Connect to restore method.
        
        # Reset Tag Usage button.
        btn_reset_usage = QPushButton(tr("reset_tag_usage"))
        btns.addButton(btn_reset_usage, QDialogButtonBox.ResetRole) # Assign ResetRole.
        btn_reset_usage.clicked.connect(self.reset_usage) # Connect to reset usage method.
        
        btns.accepted.connect(self.accept) # Connect OK to dialog's accept slot.
        btns.rejected.connect(self.reject) # Connect Cancel to dialog's reject slot.
        layout.addWidget(btns)
        logger.debug("Dialog buttons setup complete.")

    def _load_state(self) -> None:
        """
        Loads the dialog's size and position from the state manager.
        """
        if self.state_manager:
            width = self.state_manager.get("settings_width", 700)
            height = self.state_manager.get("settings_height", 500)
            self.resize(width, height)
            logger.debug(f"Loaded dialog size from state: {width}x{height}")
        else:
            logger.debug("No StateManager available to load dialog size.")

    def _choose_save_dir(self) -> None:
        """
        Opens a QFileDialog to allow the user to select a default save directory.

        The selected directory path is then set to the `edit_save_dir` QLineEdit.
        """
        # Get the current text from the line edit as the starting directory for the dialog.
        current_dir = self.edit_save_dir.text() or str(config_manager.get('default_save_directory', ''))
        dir_path = QFileDialog.getExistingDirectory(
            self, tr('default_save_dir_label'), current_dir
        )
        if dir_path:
            self.edit_save_dir.setText(dir_path)
            logger.info(f"Default save directory chosen: {dir_path}")
        else:
            logger.debug("Directory selection canceled.")

    def _add_tag_row(self) -> None:
        """
        Adds a new empty row to the tags table, allowing the user to define a new tag.
        """
        row = self.tbl_tags.rowCount() # Get the current number of rows.
        self.tbl_tags.insertRow(row) # Insert a new row at the end.
        # Set empty QTableWidgetItems for the new row's code and description.
        self.tbl_tags.setItem(row, 0, QTableWidgetItem(""))
        self.tbl_tags.setItem(row, 1, QTableWidgetItem(""))
        logger.debug(f"Added new tag row at index {row}.")

    def accept(self) -> None:
        """
        Overrides the QDialog.accept() method.

        This method is called when the user clicks the OK button. It saves all
        modified settings (general, tags, and compression) to the configuration
        manager and then closes the dialog.
        """
        logger.info("Settings dialog accepted. Saving settings...")
        self._save_general_settings() # Save settings from the general tab.
        self._save_tags() # Save changes to the tags table.
        self.compression_panel.update_cfg() # Update the config dictionary with compression settings.
        
        # Finally, save the entire configuration to disk.
        config_manager.save(self.cfg)
        super().accept() # Call base class accept to close the dialog.
        logger.info("Settings saved and dialog closed.")

    def _save_general_settings(self) -> None:
        """
        Saves the general settings from the UI fields to the internal configuration dictionary.
        """
        # Update accepted extensions.
        exts = [e.strip() for e in self.edit_ext.text().split(',') if e.strip()]
        self.cfg['accepted_extensions'] = exts
        logger.debug(f"Saved accepted_extensions: {exts}")

        # Update language and theme.
        self.cfg['language'] = self.combo_lang.currentText()
        logger.debug(f"Saved language: {self.cfg['language']}")
        self.cfg['theme'] = self.combo_theme.currentText()
        logger.debug(f"Saved theme: {self.cfg['theme']}")

        # Update default save directory.
        self.cfg['default_save_directory'] = self.edit_save_dir.text().strip()
        logger.debug(f"Saved default_save_directory: {self.cfg['default_save_directory']}")

        # Update toolbar style.
        style = 'text' if self.chk_toolbar_text.isChecked() else 'icons'
        self.cfg['toolbar_style'] = style
        logger.debug(f"Saved toolbar_style: {style}")

    def _save_tags(self) -> None:
        """
        Saves the tags from the tags table to the `tags.json` file.

        This method reads the current state of the tags table, merges it with
        existing multi-language tag data, and then writes the updated data
        back to the `tags.json` file.
        """
        lang = self.combo_lang.currentText() # Get the currently selected language.
        tags_all = load_tags_multilang() # Load the full multi-language tags dictionary.
        
        # Iterate through each row in the tags table.
        for row in range(self.tbl_tags.rowCount()):
            code_item = self.tbl_tags.item(row, 0) # Get the QTableWidgetItem for the tag code.
            desc_item = self.tbl_tags.item(row, 1) # Get the QTableWidgetItem for the tag description.
            
            if code_item and desc_item:
                code = code_item.text().strip() # Get and strip the tag code.
                desc = desc_item.text().strip() # Get and strip the tag description.
                
                if code: # Only process if the tag code is not empty.
                    # Get the existing entry for this code, or an empty dict if new.
                    entry = tags_all.get(code, {})
                    
                    # If the existing entry is not a dict (e.g., it was a plain string tag),
                    # convert it to a dict with the current language's description.
                    if not isinstance(entry, dict):
                        entry = {lang: desc}
                    else:
                        # Otherwise, update the description for the current language.
                        entry[lang] = desc
                    tags_all[code] = entry # Update the main tags dictionary.
                    logger.debug(f"Saved tag '{code}' with description for '{lang}': '{desc}'")
                else:
                    logger.warning(f"Skipping empty tag code at row {row} in tags table.")
            else:
                logger.warning(f"Missing tag code or description item at row {row} in tags table.")

        try:
            # Save the updated tags_all dictionary to the default tags file.
            # `ensure_ascii=False` allows non-ASCII characters (e.g., German umlauts) to be saved directly.
            with open(DEFAULT_TAGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(tags_all, f, indent=2, ensure_ascii=False)
            logger.info(f"Tags successfully saved to {DEFAULT_TAGS_FILE}.")
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Failed to save tags to {DEFAULT_TAGS_FILE}: {e}")
            QMessageBox.warning(self, tr("error"), tr("tags_save_failed").format(error=e))
        except Exception as e:
            logger.error(f"An unexpected error occurred while saving tags: {e}")
            QMessageBox.warning(self, tr("error"), f"An unexpected error occurred while saving tags: {e}")

    def _remove_selected_tag_row(self) -> None:
        """
        Removes the currently selected row(s) from the tags table.
        """
        # Get a sorted list of selected row indices in reverse order to avoid issues when removing.
        selected_rows = sorted({idx.row() for idx in self.tbl_tags.selectionModel().selectedRows()}, reverse=True)
        if not selected_rows:
            logger.info("No tag rows selected for removal.")
            return

        # Confirm deletion with the user.
        reply = QMessageBox.question(
            self,
            tr("remove_selected"),
            tr("confirm_remove_tags").format(count=len(selected_rows)), # Assuming a translation key for confirmation
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.No:
            logger.debug("Tag row removal canceled by user.")
            return

        for row in selected_rows:
            # Get the tag code before removing the row for logging.
            code_item = self.tbl_tags.item(row, 0)
            tag_code = code_item.text() if code_item else "Unknown"
            self.tbl_tags.removeRow(row)
            logger.info(f"Removed tag row for code: {tag_code} at index {row}.")
        logger.info(f"Removed {len(selected_rows)} tag rows.")

    def _update_tags_from_github(self) -> None:
        """
        Downloads the latest tags.json from a GitHub repository and updates the local file.
        New tags are added, and existing tag descriptions are updated.
        """
        github_url = "https://raw.githubusercontent.com/juergenaltemeier/mic-renamer/main/mic_renamer/config/tags.json"

        if not github_url:
            QMessageBox.warning(self, tr("error"), tr("github_url_not_configured"))
            return

        try:
            response = requests.get(github_url, timeout=10)
            response.raise_for_status()
            github_tags = response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download tags from GitHub: {e}")
            QMessageBox.warning(self, tr("error"), tr("tags_download_failed").format(error=e))
            return
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse tags from GitHub: {e}")
            QMessageBox.warning(self, tr("error"), tr("tags_parse_failed").format(error=e))
            return

        try:
            with open(DEFAULT_TAGS_FILE, 'r', encoding='utf-8') as f:
                local_tags = json.load(f)
        except (IOError, json.JSONDecodeError):
            local_tags = {}

        # Merge tags
        merged_tags = local_tags.copy()
        for tag, description in github_tags.items():
            merged_tags[tag] = description

        reply = QMessageBox.question(
            self,
            tr("update_tags"),
            tr("confirm_update_tags"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                with open(DEFAULT_TAGS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(merged_tags, f, indent=2, ensure_ascii=False)
                logger.info(f"Tags successfully updated from {github_url}.")
                QMessageBox.information(self, tr("success"), tr("tags_update_success"))
            except IOError as e:
                logger.error(f"Failed to write updated tags to {DEFAULT_TAGS_FILE}: {e}")
                QMessageBox.warning(self, tr("error"), tr("tags_write_failed").format(error=e))

    def reset_usage(self) -> None:
        """
        Resets all stored tag usage statistics.

        This action is typically confirmed with the user before execution.
        """
        reply = QMessageBox.question(
            self,
            tr("reset_tag_usage"),
            tr("confirm_reset_tag_usage"), # Assuming a translation key for confirmation
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.No:
            logger.debug("Tag usage reset canceled by user.")
            return

        reset_counts() # Call the function from tag_usage module to reset counts.
        logger.info("Tag usage statistics reset.")
        QMessageBox.information(self, tr("done"), tr("tag_usage_reset_done")) # Assuming a translation key

    def restore_defaults(self) -> None:
        """
        Restores the application settings to their factory default values.

        This is a destructive operation that deletes the user's configuration
        directory and then exits the application, requiring a restart.
        A confirmation dialog is shown before proceeding.
        """
        title = tr("restore_defaults")
        msg = (
            tr("restore_defaults_confirm_msg") # Assuming a translation key for this long message.
        )
        reply = QMessageBox.question(
            self, title, msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            logger.debug("Restore defaults canceled by user.")
            return

        try:
            config_manager.restore_defaults()
            logger.info("Restored default settings.")
            
            QMessageBox.information(
                self,
                title,
                tr("restore_defaults_done_msg"), # Assuming a translation key for this message.
            )
            self.accept() # Accept and close the dialog

        except Exception as e:
            logger.critical(f"An unexpected error occurred during restore defaults: {e}")
            QMessageBox.critical(self, title, tr("unexpected_error_reset_settings").format(error=e))

    def closeEvent(self, event) -> None:
        """
        Handles the dialog closing event.

        Saves the dialog's current size and position to the state manager
        before the dialog closes.

        Args:
            event (QCloseEvent): The close event.
        """
        logger.info("Settings dialog closing.")
        if self.state_manager:
            self.state_manager.set("settings_width", self.width())
            self.state_manager.set("settings_height", self.height())
            self.state_manager.save()
            logger.debug("Saved dialog size to state.")
        else:
            logger.debug("No StateManager available to save dialog size.")
        super().closeEvent(event)