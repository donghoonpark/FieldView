import pytest
from PySide6.QtGui import QFont
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

def test_collision_avoidance(qtbot):
    dc = DataContainer()
    # Two points very close to each other
    dc.set_data([[0, 0], [1, 1]], [10, 20], ["A", "B"])
    layer = LabelLayer(dc)
    layer.collision_avoidance_enabled = True
    layer.collision_offset_factor = 1.5 # Increase offset to ensure separation
    
    # Mock font metrics or use real one
    # We need to trigger paint or calculate_layout manually
    # Since calculate_layout is internal, we can access it for testing
    
    from PySide6.QtGui import QFontMetrics, QPainter, QImage
    
    # Create a dummy painter to get metrics
    img = QImage(100, 100, QImage.Format.Format_ARGB32)
    painter = QPainter(img)
    painter.setFont(layer.font)
    metrics = painter.fontMetrics()
    painter.end()
    
    indices, points, values, labels = layer.get_valid_data(return_indices=True)
    layout = layer._calculate_layout(indices, points, values, labels, metrics)

    rect0 = layout[0]
    rect1 = layout[1]

    # They should not intersect
    assert not rect0.intersects(rect1)

def test_highlight_indices_respect_exclusions(qtbot):
    dc = DataContainer()
    dc.set_data([[0, 0], [10, 0], [20, 0]], [1, 2, 3], ["A", "B", "C"])
    layer = LabelLayer(dc)
    layer.set_excluded_indices([1])
    layer.set_highlighted_indices([2])

    from PySide6.QtGui import QPainter, QImage

    img = QImage(200, 200, QImage.Format.Format_ARGB32)
    painter = QPainter(img)
    painter.setFont(layer.font)
    metrics = painter.fontMetrics()
    painter.end()

    indices, points, values, labels = layer.get_valid_data(return_indices=True)
    layout = layer._calculate_layout(indices, points, values, labels, metrics)

    assert set(layout.keys()) == {0, 2}
    assert 2 in layer.highlighted_indices

def test_font_loading(qtbot):
    dc = DataContainer()
    layer = LabelLayer(dc)
    
    assert layer.font is not None
    assert layer.font.family() in ["JetBrains Mono", "Monospace"] or layer.font.styleHint() == QFont.StyleHint.Monospace
