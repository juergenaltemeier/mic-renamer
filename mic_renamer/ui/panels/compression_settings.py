"""Panel for configuring image compression settings."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QFormLayout,
    QDoubleSpinBox,
    QSpinBox,
    QCheckBox,
    QPushButton,
)

from ... import config_manager
from ...utils.i18n import tr


class CompressionSettingsPanel(QWidget):
    """UI for compression related settings."""

    def __init__(self, cfg: dict):
        super().__init__()
        self.cfg = cfg
        layout = QFormLayout(self)

        self.spin_size = QDoubleSpinBox()
        self.spin_size.setRange(10, 100000)
        self.spin_size.setSuffix(" KB")
        self.spin_size.setValue(float(cfg.get("compression_max_size_kb", 2048)))
        layout.addRow(tr("max_size_label"), self.spin_size)

        self.spin_quality = QSpinBox()
        self.spin_quality.setRange(1, 100)
        self.spin_quality.setValue(int(cfg.get("compression_quality", 95)))
        layout.addRow(tr("quality_label"), self.spin_quality)

        self.chk_reduce = QCheckBox(tr("reduce_resolution_label"))
        self.chk_reduce.setChecked(cfg.get("compression_reduce_resolution", True))
        layout.addRow(self.chk_reduce)

        self.chk_resize_only = QCheckBox(tr("resize_only_label"))
        self.chk_resize_only.setChecked(cfg.get("compression_resize_only", False))
        layout.addRow(self.chk_resize_only)

        self.btn_reset = QPushButton(tr("restore_defaults"))
        layout.addRow(self.btn_reset)
        self.btn_reset.clicked.connect(self.restore_defaults)

    def update_cfg(self) -> None:
        self.cfg["compression_max_size_kb"] = self.spin_size.value()
        self.cfg["compression_quality"] = self.spin_quality.value()
        self.cfg["compression_reduce_resolution"] = self.chk_reduce.isChecked()
        self.cfg["compression_resize_only"] = self.chk_resize_only.isChecked()

    def restore_defaults(self) -> None:
        defaults = config_manager.restore_defaults()
        self.spin_size.setValue(float(defaults.get("compression_max_size_kb", 2048)))
        self.spin_quality.setValue(int(defaults.get("compression_quality", 95)))
        self.chk_reduce.setChecked(defaults.get("compression_reduce_resolution", True))
        self.chk_resize_only.setChecked(defaults.get("compression_resize_only", False))
        # reload since restore_defaults overwrote file
        self.cfg.update(config_manager.load())
