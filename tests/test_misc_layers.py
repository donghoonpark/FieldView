import pytest
import os
from PySide6.QtGui import QPixmap
from PySide6.QtCore import QByteArray
from fieldview.core.data_container import DataContainer
from fieldview.layers.svg_layer import SvgLayer
from fieldview.layers.pin_layer import PinLayer

def test_svg_layer(qtbot, tmp_path):
    layer = SvgLayer()
    
    # Create a dummy SVG file
    svg_content = b'<svg width="100" height="100"><circle cx="50" cy="50" r="40" stroke="green" stroke-width="4" fill="yellow" /></svg>'
    svg_file = tmp_path / "test.svg"
    svg_file.write_bytes(svg_content)
    
    layer.load_svg(str(svg_file))
    assert layer._renderer.isValid()

def test_pin_layer(qtbot):
    dc = DataContainer()
    dc.set_data([[0, 0]], [10])
    layer = PinLayer(dc)
    
    # Create a dummy pixmap
    pixmap = QPixmap(10, 10)
    layer.set_icon(pixmap)
    
    assert layer.icon == pixmap
