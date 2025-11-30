import pytest
import numpy as np
from fieldview.core.data_container import DataContainer

def test_initialization():
    dc = DataContainer()
    assert len(dc.points) == 0
    assert len(dc.values) == 0

def test_set_data(qtbot):
    dc = DataContainer()
    points = [[0, 0], [1, 1]]
    values = [10, 20]
    
    with qtbot.waitSignal(dc.dataChanged):
        dc.set_data(points, values)
        
    assert len(dc.points) == 2
    assert np.array_equal(dc.values, np.array([10, 20]))

def test_add_points(qtbot):
    dc = DataContainer()
    dc.set_data([[0, 0]], [10])
    
    with qtbot.waitSignal(dc.dataChanged):
        dc.add_points([[1, 1]], [20])
        
    assert len(dc.points) == 2
    assert dc.values[1] == 20

def test_update_point(qtbot):
    dc = DataContainer()
    dc.set_data([[0, 0]], [10])
    
    with qtbot.waitSignal(dc.dataChanged):
        dc.update_point(0, value=50)
        
    assert dc.values[0] == 50

def test_remove_points(qtbot):
    dc = DataContainer()
    dc.set_data([[0, 0], [1, 1], [2, 2]], [10, 20, 30])
    
    with qtbot.waitSignal(dc.dataChanged):
        dc.remove_points([1])
        
    assert len(dc.points) == 2
    assert dc.values[1] == 30 # The old index 2 is now index 1

def test_get_closest_point():
    dc = DataContainer()
    dc.set_data([[0, 0], [10, 10]], [1, 2])
    
    idx = dc.get_closest_point(1, 1)
    assert idx == 0
    
    idx = dc.get_closest_point(9, 9)
    assert idx == 1
    
    idx = dc.get_closest_point(5, 5) # Equidistant (approx), returns one of them
    assert idx is not None

def test_get_closest_point_threshold():
    dc = DataContainer()
    dc.set_data([[0, 0]], [1])
    
    idx = dc.get_closest_point(100, 100, threshold=10)
    assert idx is None
