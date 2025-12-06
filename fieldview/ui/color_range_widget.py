from qtpy.QtCore import Signal
from qtpy.QtGui import QPainter, QLinearGradient, QColor
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import (
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QDoubleSpinBox,
    )
    from PySide6.QtCore import Signal
else:
    from qtpy.QtWidgets import (
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QDoubleSpinBox,
    )
    from qtpy.QtCore import Signal

from fieldview.rendering.colormaps import get_colormap


class _ColorBar(QWidget):
    """Simple horizontal color bar that visualizes a colormap."""

    def __init__(self, colormap_name: str = "viridis", parent=None):
        super().__init__(parent)
        self._colormap = get_colormap(colormap_name)
        self.setMinimumHeight(18)

    @property
    def colormap_name(self) -> str:
        return self._colormap.name

    def set_colormap(self, name: str):
        self._colormap = get_colormap(name)
        self.update()

    def paintEvent(self, event):  # noqa: N802 - Qt naming convention
        painter = QPainter(self)
        rect = self.rect()

        gradient = QLinearGradient(rect.topLeft(), rect.topRight())
        lut = self._colormap.get_lut(256)

        # Sample several stops across the LUT to build a smooth gradient
        for i in range(0, 256, 16):
            position = i / 255
            gradient.setColorAt(position, QColor.fromRgba(int(lut[i])))
        gradient.setColorAt(1.0, QColor.fromRgba(int(lut[-1])))

        painter.fillRect(rect, gradient)


class ColorRangeControl(QWidget):
    """Composite widget with a color bar and spin boxes for color min/max."""

    colorRangeChanged = Signal(float, float)

    def __init__(self, colormap_name: str = "viridis", parent=None):
        super().__init__(parent)
        self._updating = False

        self._colorbar = _ColorBar(colormap_name)

        self._min_spin = QDoubleSpinBox()
        self._min_spin.setRange(-1e9, 1e9)
        self._min_spin.setDecimals(4)
        self._min_spin.setValue(0.0)

        self._max_spin = QDoubleSpinBox()
        self._max_spin.setRange(-1e9, 1e9)
        self._max_spin.setDecimals(4)
        self._max_spin.setValue(1.0)

        self._min_spin.valueChanged.connect(self._on_spin_changed)
        self._max_spin.valueChanged.connect(self._on_spin_changed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._colorbar)

        spin_layout = QHBoxLayout()
        spin_layout.addWidget(QLabel("Min:"))
        spin_layout.addWidget(self._min_spin)
        spin_layout.addWidget(QLabel("Max:"))
        spin_layout.addWidget(self._max_spin)
        layout.addLayout(spin_layout)

    @property
    def colorbar(self):
        return self._colorbar

    @property
    def minimum_value(self) -> float:
        return self._min_spin.value()

    @property
    def maximum_value(self) -> float:
        return self._max_spin.value()

    def set_colormap(self, name: str):
        self._colorbar.set_colormap(name)

    def set_range(self, color_min: float, color_max: float, emit_signal: bool = True):
        """Updates the spin boxes while keeping their ordering consistent."""
        if color_min > color_max:
            color_max = color_min

        self._updating = True
        self._min_spin.setValue(color_min)
        self._max_spin.setValue(color_max)
        self._updating = False

        if emit_signal:
            self.colorRangeChanged.emit(color_min, color_max)

    def _on_spin_changed(self, value: float):  # noqa: ARG002 - required by Qt
        if self._updating:
            return

        sender = self.sender()
        min_val = self._min_spin.value()
        max_val = self._max_spin.value()

        if min_val > max_val:
            self._updating = True
            if sender is self._min_spin:
                self._max_spin.setValue(min_val)
                max_val = min_val
            else:
                self._min_spin.setValue(max_val)
                min_val = max_val
            self._updating = False

        self.colorRangeChanged.emit(min_val, max_val)
