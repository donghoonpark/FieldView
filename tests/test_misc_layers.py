import pytest
import os
from qtpy.QtCore import QPointF, QRectF
from qtpy.QtGui import QPixmap, QPainter, QColor
from qtpy.QtSvgWidgets import QGraphicsSvgItem
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


def test_svg_layer_origin(qtbot):
    layer = SvgLayer()

    base_rect = layer.boundingRect()
    layer.set_origin((10, -5))

    shifted_rect = layer.boundingRect()

    assert shifted_rect.left() == base_rect.left() + 10
    assert shifted_rect.top() == base_rect.top() - 5
    assert shifted_rect.size() == base_rect.size()


def test_svg_layer_origin_absolute(qtbot):
    layer = SvgLayer()

    base_rect = layer.boundingRect()

    layer.set_origin((5, 5))
    initial = layer.boundingRect()

    layer.set_origin((12, -3))
    updated = layer.boundingRect()

    assert initial.left() == base_rect.left() + 5
    assert updated.left() == base_rect.left() + 12
    assert updated.top() == base_rect.top() - 3
    assert updated.size() == base_rect.size()

def test_pin_layer(qtbot):
    dc = DataContainer()
    dc.set_data([[0, 0]], [10])
    layer = PinLayer(dc)
    
    # Create a dummy pixmap
    pixmap = QPixmap(10, 10)
    layer.set_icon(pixmap)
    
    assert layer.icon == pixmap
