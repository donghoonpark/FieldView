import pytest
from fieldview.core.data_container import DataContainer
from fieldview.layers.text_layer import ValueLayer, LabelLayer

def test_value_layer(qtbot):
    dc = DataContainer()
    dc.set_data([[0, 0]], [10.12345])
    layer = ValueLayer(dc)
    
    # Default 2 decimals
    assert layer._get_text(0, 10.12345, "") == "10.12"
    
    layer.decimal_places = 3
    assert layer._get_text(0, 10.12345, "") == "10.123"
    
    layer.suffix = " m"
    assert layer._get_text(0, 10.12345, "") == "10.123 m"
    
    layer.prefix = "Val: "
    assert layer._get_text(0, 10.12345, "") == "Val: 10.123 m"

def test_label_layer(qtbot):
    dc = DataContainer()
    dc.set_data([[0, 0]], [10], ["Test Label"])
    layer = LabelLayer(dc)
    
    assert layer._get_text(0, 10, "Test Label") == "Test Label"

def test_highlighting(qtbot):
    dc = DataContainer()
    layer = ValueLayer(dc)
    
    layer.set_highlighted_indices([0, 2])
    assert layer.highlighted_indices == {0, 2}
