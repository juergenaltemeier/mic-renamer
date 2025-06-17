"""Panel for configuring image compression settings."""
from __future__ import annotations

from pathlib import Path

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

        self.chk_reduce = EnterToggleCheckBox(tr("reduce_resolution_label"))
        self.chk_reduce.setChecked(cfg.get("compression_reduce_resolution", True))
        layout.addRow(self.chk_reduce)

        self.chk_resize_only = EnterToggleCheckBox(tr("resize_only_label"))
        self.chk_resize_only.setChecked(cfg.get("compression_resize_only", False))
        layout.addRow(self.chk_resize_only)

        self.spin_max_w = QSpinBox()
        self.spin_max_w.setRange(0, 10000)
        self.spin_max_w.setValue(int(cfg.get("compression_max_width", 0)))
        layout.addRow(tr("max_width_label"), self.spin_max_w)

        self.spin_max_h = QSpinBox()
        self.spin_max_h.setRange(0, 10000)
        self.spin_max_h.setValue(int(cfg.get("compression_max_height", 0)))
        layout.addRow(tr("max_height_label"), self.spin_max_h)

        self.btn_reset = QPushButton(tr("restore_defaults"))
        layout.addRow(self.btn_reset)
        self.btn_reset.clicked.connect(self.restore_defaults)

    def update_cfg(self) -> None:
        self.cfg["compression_max_size_kb"] = self.spin_size.value()
        self.cfg["compression_quality"] = self.spin_quality.value()
        self.cfg["compression_reduce_resolution"] = self.chk_reduce.isChecked()
        self.cfg["compression_resize_only"] = self.chk_resize_only.isChecked()
        self.cfg["compression_max_width"] = self.spin_max_w.value()
        self.cfg["compression_max_height"] = self.spin_max_h.value()

    def restore_defaults(self) -> None:
        defaults = config_manager.restore_defaults()
        self.spin_size.setValue(float(defaults.get("compression_max_size_kb", 2048)))
        self.spin_quality.setValue(int(defaults.get("compression_quality", 95)))
        self.chk_reduce.setChecked(defaults.get("compression_reduce_resolution", True))
        self.chk_resize_only.setChecked(defaults.get("compression_resize_only", False))
        self.spin_max_w.setValue(int(defaults.get("compression_max_width", 0)))
        self.spin_max_h.setValue(int(defaults.get("compression_max_height", 0)))
        # reload since restore_defaults overwrote file
        self.cfg.update(config_manager.load())
