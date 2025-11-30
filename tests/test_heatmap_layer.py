import pytest
import numpy as np
from PySide6.QtCore import QTimer, QPointF
from PySide6.QtGui import QPolygonF
from fieldview.core.data_container import DataContainer
from fieldview.layers.heatmap_layer import HeatmapLayer

def test_heatmap_initialization(qtbot):
    dc = DataContainer()
    layer = HeatmapLayer(dc)
    # Default shape is a square 300x300 centered at 0
    rect = layer.boundingRect()
    assert rect.width() == 300
    assert rect.height() == 300

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

def test_boundary_points_generation():
    dc = DataContainer()
    layer = HeatmapLayer(dc)
    
    # Set a simple square polygon
    polygon = QPolygonF([
        QPointF(0, 0), QPointF(100, 0),
        QPointF(100, 100), QPointF(0, 100)
    ])
    layer.set_boundary_shape(polygon)
    
    points = np.array([[10, 10], [90, 90]])
    values = np.array([0, 10])
    
    b_points, b_values = layer._generate_boundary_points(points, values)
    
    assert len(b_points) > 0
    assert len(b_values) == len(b_points)
    
    # Check if boundary points are on the polygon perimeter
    # Simple check: x is 0 or 100, or y is 0 or 100
    on_boundary = np.isclose(b_points[:, 0], 0) | np.isclose(b_points[:, 0], 100) | \
                  np.isclose(b_points[:, 1], 0) | np.isclose(b_points[:, 1], 100)
    assert np.all(on_boundary)

def test_not_enough_points(qtbot):
    dc = DataContainer()
    layer = HeatmapLayer(dc)
    
    dc.set_data([[0, 0]], [10])
    assert layer._cached_image is None
