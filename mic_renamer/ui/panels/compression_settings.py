"""
This module defines the `CompressionSettingsPanel` class, a QWidget panel for
configuring image compression settings within the application. It provides UI
controls for maximum file size, JPEG quality, resolution reduction, and image
dimensions, and allows restoring default compression settings.
"""
from __future__ import annotations

import logging
from typing import Dict, Any

from PySide6.QtWidgets import (
    QWidget,
    QFormLayout,
    QDoubleSpinBox,
    QSpinBox,
    QPushButton,
)
from ..components import EnterToggleCheckBox

from ... import config_manager
from ...utils.i18n import tr

logger = logging.getLogger(__name__)


class CompressionSettingsPanel(QWidget):
    """
    A QWidget panel for configuring image compression-related settings.

    This panel provides input fields and checkboxes for various compression parameters
    such as target file size, JPEG quality, and image dimensions. It interacts with
    the `config_manager` to load and update these settings.
    """

    def __init__(self, cfg: Dict[str, Any]):
        """
        Initializes the CompressionSettingsPanel.

        Args:
            cfg (Dict[str, Any]): A dictionary representing the current application
                                  configuration. This panel will read from and update
                                  this dictionary.
        """
        super().__init__()
        self.cfg = cfg # Store reference to the configuration dictionary.
        logger.info("CompressionSettingsPanel initialized.")
        self._setup_ui() # Build the UI components.

    def _setup_ui(self) -> None:
        """
        Sets up the user interface elements of the compression settings panel.

        This includes spin boxes for numeric inputs (size, quality, dimensions)
        and checkboxes for boolean options (reduce resolution, resize only).
        """
        layout = QFormLayout(self) # Use a QFormLayout for label-input pairs.

        # Max Size (KB) setting.
        self.spin_size = QDoubleSpinBox()
        self.spin_size.setRange(10, 100000) # Allow sizes from 10 KB to 100 MB.
        self.spin_size.setSuffix(" KB") # Display " KB" suffix.
        # Set initial value from config, defaulting to 2048 KB (2 MB).
        self.spin_size.setValue(float(self.cfg.get("compression_max_size_kb", 2048)))
        self.spin_size.setToolTip(tr("max_size_desc")) # Tooltip for user guidance.
        layout.addRow(tr("max_size_label"), self.spin_size)
        logger.debug(f"Max size spin box initialized to {self.spin_size.value()} KB.")

        # JPEG Quality setting.
        self.spin_quality = QSpinBox()
        self.spin_quality.setRange(1, 100) # Quality from 1% to 100%.
        # Set initial value from config, defaulting to 95%.
        self.spin_quality.setValue(int(self.cfg.get("compression_quality", 95)))
        self.spin_quality.setToolTip(tr("quality_desc"))
        layout.addRow(tr("quality_label"), self.spin_quality)
        logger.debug(f"Quality spin box initialized to {self.spin_quality.value()}%")

        # Reduce Resolution checkbox.
        self.chk_reduce = EnterToggleCheckBox(tr("reduce_resolution_label"))
        self.chk_reduce.setChecked(self.cfg.get("compression_reduce_resolution", True))
        self.chk_reduce.setToolTip(tr("reduce_resolution_desc"))
        layout.addRow(self.chk_reduce)
        logger.debug(f"Reduce resolution checkbox initialized to {self.chk_reduce.isChecked()}.")

        # Resize Only checkbox.
        self.chk_resize_only = EnterToggleCheckBox(tr("resize_only_label"))
        self.chk_resize_only.setChecked(self.cfg.get("compression_resize_only", False))
        self.chk_resize_only.setToolTip(tr("resize_only_desc"))
        layout.addRow(self.chk_resize_only)
        logger.debug(f"Resize only checkbox initialized to {self.chk_resize_only.isChecked()}.")

        # Max Width (px) setting.
        self.spin_max_w = QSpinBox()
        self.spin_max_w.setRange(0, 10000) # Width from 0 (no limit) to 10000 pixels.
        self.spin_max_w.setValue(int(self.cfg.get("compression_max_width", 0)))
        self.spin_max_w.setToolTip(tr("max_width_desc"))
        layout.addRow(tr("max_width_label"), self.spin_max_w)
        logger.debug(f"Max width spin box initialized to {self.spin_max_w.value()}px.")

        # Max Height (px) setting.
        self.spin_max_h = QSpinBox()
        self.spin_max_h.setRange(0, 10000) # Height from 0 (no limit) to 10000 pixels.
        self.spin_max_h.setValue(int(self.cfg.get("compression_max_height", 0)))
        self.spin_max_h.setToolTip(tr("max_height_desc"))
        layout.addRow(tr("max_height_label"), self.spin_max_h)
        logger.debug(f"Max height spin box initialized to {self.spin_max_h.value()}px.")

        # Restore Defaults button.
        self.btn_reset = QPushButton(tr("restore_defaults"))
        layout.addRow(self.btn_reset)
        self.btn_reset.clicked.connect(self.restore_defaults) # Connect to restore defaults method.
        logger.debug("Restore defaults button added.")

    def update_cfg(self) -> None:
        """
        Updates the internal configuration dictionary (`self.cfg`) with the current
        values from the UI input fields.

        This method should be called before saving the configuration to disk.
        """
        self.cfg["compression_max_size_kb"] = self.spin_size.value()
        self.cfg["compression_quality"] = self.spin_quality.value()
        self.cfg["compression_reduce_resolution"] = self.chk_reduce.isChecked()
        self.cfg["compression_resize_only"] = self.chk_resize_only.isChecked()
        self.cfg["compression_max_width"] = self.spin_max_w.value()
        self.cfg["compression_max_height"] = self.spin_max_h.value()
        logger.info("Compression settings updated in internal config.")

    def restore_defaults(self) -> None:
        """
        Restores the compression settings displayed in the UI to their default values.

        This method retrieves default values from the `config_manager` and updates
        the UI elements accordingly. It also reloads the main configuration to ensure
        `self.cfg` is synchronized after `config_manager.restore_defaults()` might
        have overwritten the config file.
        """
        logger.info("Restoring compression settings to defaults.")
        # Call config_manager's restore_defaults to get the default values.
        # Note: this also overwrites the app_settings.yaml file.
        defaults = config_manager.restore_defaults()
        
        # Update UI elements with default values.
        self.spin_size.setValue(float(defaults.get("compression_max_size_kb", 2048)))
        self.spin_quality.setValue(int(defaults.get("compression_quality", 95)))
        self.chk_reduce.setChecked(defaults.get("compression_reduce_resolution", True))
        self.chk_resize_only.setChecked(defaults.get("compression_resize_only", False))
        self.spin_max_w.setValue(int(defaults.get("compression_max_width", 0)))
        self.spin_max_h.setValue(int(defaults.get("compression_max_height", 0)))
        
        # Reload the main configuration into self.cfg to ensure it reflects the changes
        # made by config_manager.restore_defaults() which writes to disk.
        self.cfg.update(config_manager.load())
        logger.info("Compression settings UI updated to defaults.")