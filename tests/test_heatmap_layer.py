import pytest
import numpy as np
from PySide6.QtCore import QTimer
from fieldview.core.data_container import DataContainer
from fieldview.layers.heatmap_layer import HeatmapLayer

def test_heatmap_initialization(qtbot):
    dc = DataContainer()
    layer = HeatmapLayer(dc)
    assert layer.radius == 150.0

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
    
    points = np.array([[0, 0], [10, 0]])
    values = np.array([0, 10])
    
    b_points, b_values = layer._generate_boundary_points(points, values)
    
    assert len(b_points) > 0
    assert len(b_values) == len(b_points)
    
    # Check if boundary points are on the circle
    radii = np.sqrt(np.sum(b_points**2, axis=1))
    assert np.allclose(radii, layer.radius)

def test_not_enough_points(qtbot):
    dc = DataContainer()
    layer = HeatmapLayer(dc)
    
    dc.set_data([[0, 0]], [10])
    assert layer._cached_image is None
