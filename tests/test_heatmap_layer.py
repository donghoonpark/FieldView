import pytest
import numpy as np
from PySide6.QtCore import QTimer, QPointF, QRectF
from PySide6.QtGui import QPolygonF, QPainterPath, QColor
from fieldview.core.data_container import DataContainer
from fieldview.layers.heatmap_layer import HeatmapLayer

def test_heatmap_initialization(qtbot):
    dc = DataContainer()
    layer = HeatmapLayer(dc)
    # Default shape is empty until data is set or manually defined
    rect = layer.boundingRect()
    assert rect.width() == 0
    assert rect.height() == 0

def test_heatmap_update(qtbot):
    dc = DataContainer()
    layer = HeatmapLayer(dc)
    
    # Add enough points for interpolation
    points = np.random.rand(10, 2) * 100
    values = np.random.rand(10) * 100
    
    with qtbot.waitSignal(dc.dataChanged):
        dc.set_data(points, values)
        
    # Check if image is generated (Fast update)
    assert layer._cached_image is not None
    
    # Wait for HQ update
    qtbot.wait(400) # Wait > 300ms
    assert layer._cached_image is not None

    # _generate_boundary_points was removed and refactored into BoundaryPointGenerator
    # This logic is now tested in test_interpolation.py or implicitly via rendering
    pass

def test_not_enough_points(qtbot):
    dc = DataContainer()
    layer = HeatmapLayer(dc)
    
    dc.set_data([[0, 0]], [10])
    assert layer._cached_image is None

def test_rendering_signal(qtbot):
    dc = DataContainer()
    layer = HeatmapLayer(dc)
    
    # Connect signal
    with qtbot.waitSignal(layer.renderingFinished, timeout=1000) as blocker:
        points = np.random.rand(10, 2) * 100
        values = np.random.rand(10) * 100
        dc.set_data(points, values)
        
    assert isinstance(blocker.args[0], float)
    assert blocker.args[0] >= 0

def test_boundary_shape_types(qtbot):
    dc = DataContainer()
    layer = HeatmapLayer(dc)
    
    # Test QRectF
    rect = QRectF(0, 0, 100, 100)
    layer.set_boundary_shape(rect)
    assert not layer._boundary_shape.isEmpty()
    
    # Test QPainterPath
    path = QPainterPath()
    path.addEllipse(0, 0, 100, 100)
    layer.set_boundary_shape(path)
    assert not layer._boundary_shape.isEmpty()

def test_colormap_property(qtbot):
    dc = DataContainer()
    layer = HeatmapLayer(dc)

    layer.colormap = "magma"
    assert layer.colormap == "magma"
    assert layer._colormap.name == "magma"

    layer.colormap = "viridis"
    assert layer.colormap == "viridis"


def test_heatmap_color_range_manual_and_auto(qtbot):
    dc = DataContainer()
    layer = HeatmapLayer(dc)

    # Explicit bounds should drive normalization
    layer.set_color_range(2.0, 8.0)
    grid = np.array([[0.0, 5.0], [10.0, -1.0]])
    image = layer._array_to_qimage(grid)

    lut = layer._colormap.get_lut(256)
    expected_low = np.clip((0.0 - 2.0) / (8.0 - 2.0), 0.0, 1.0)
    expected_high = np.clip((10.0 - 2.0) / (8.0 - 2.0), 0.0, 1.0)

    low_color = image.pixelColor(0, 0)
    mid_color = image.pixelColor(1, 0)
    high_color = image.pixelColor(0, 1)
    mask_color = image.pixelColor(1, 1)

    assert low_color == QColor.fromRgba(int(lut[int(expected_low * 255)]))
    assert mid_color == QColor.fromRgba(int(lut[int(0.5 * 255)]))
    assert high_color == QColor.fromRgba(int(lut[255]))
    assert mask_color.alpha() == 0

    # Auto bounds use incoming data when range is cleared
    layer.set_color_range(None, None)
    auto_image = layer._array_to_qimage(grid)
    auto_low_color = auto_image.pixelColor(0, 0)
    auto_high_color = auto_image.pixelColor(0, 1)

    assert auto_low_color == QColor.fromRgba(int(lut[0]))
    assert auto_high_color == QColor.fromRgba(int(lut[255]))


def test_heatmap_color_range_validation(qtbot):
    dc = DataContainer()
    layer = HeatmapLayer(dc)

    with pytest.raises(ValueError):
        layer.set_color_range(5, 5)
