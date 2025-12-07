import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtCore import Qt, QPoint, QPointF
else:
    from qtpy.QtCore import Qt, QPoint, QPointF

from fieldview.core.data_container import DataContainer
from fieldview.ui.field_view import FieldView
from fieldview.layers.heatmap_layer import HeatmapLayer
from fieldview.layers.pin_layer import PinLayer


def test_field_view_init(qtbot):
    view = FieldView()
    qtbot.addWidget(view)
    assert view.scene() is not None
    assert isinstance(view.data_container, DataContainer)


def test_field_view_interaction(qtbot):
    view = FieldView()
    qtbot.addWidget(view)
    view.resize(400, 400)
    view.show()

    # Initial scale
    initial_transform = view.transform()

    # Simulate Wheel Event
    # We need to construct a QWheelEvent manually or use qtbot
    # qtbot doesn't have a direct 'wheel' method easily accessible for all bindings sometimes,
    # but let's try calling wheelEvent directly with a mock event if needed,
    # or better, use QTest if available via qtbot.

    # However, constructing QWheelEvent is tricky across bindings (Qt5 vs Qt6).
    # Let's try to invoke the method directly with a mocked event object to test logic.

    class MockWheelEvent:
        def __init__(self, angle_y):
            self._angle_y = angle_y

        def angleDelta(self):
            val = self._angle_y

            class Point:
                def y(self):
                    return val

            return Point()

        def position(self):
            # Qt6 style
            return QPointF(100, 100)

        def pos(self):
            # Qt5 style
            return QPoint(100, 100)

        def modifiers(self):
            return Qt.KeyboardModifier.NoModifier

    # Test Zoom In
    event_in = MockWheelEvent(120)
    view.wheelEvent(event_in)

    # Check if scaled up
    assert view.transform().m11() > initial_transform.m11()

    # Test Zoom Out
    event_out = MockWheelEvent(-120)
    view.wheelEvent(event_out)

    # Check if scaled down (should be close to initial)
    # Note: floating point precision might not be exact
    assert view.transform().m11() < initial_transform.m11() * 1.2  # roughly back


def test_field_view_set_data(qtbot):
    view = FieldView()
    qtbot.addWidget(view)

    points = np.array([[0, 0], [10, 10]])
    values = np.array([1, 2])
    view.set_data(points, values)

    assert len(view.data_container.points) == 2
    assert len(view.data_container.values) == 2


def test_field_view_add_layers(qtbot):
    view = FieldView()
    qtbot.addWidget(view)

    # Heatmap
    heatmap = view.add_heatmap_layer()
    assert isinstance(heatmap, HeatmapLayer)
    assert heatmap in view.scene().items()
    assert view.layers["heatmap"] == heatmap

    # Pin
    pin = view.add_pin_layer()
    assert isinstance(pin, PinLayer)
    assert pin in view.scene().items()
    assert view.layers["pin"] == pin


def test_field_view_fit_to_scene(qtbot):
    view = FieldView()
    qtbot.addWidget(view)
    view.resize(400, 300)

    # Add some content
    points = np.array([[0, 0], [100, 100]])
    values = np.array([0, 1])
    view.set_data(points, values)
    view.add_pin_layer()

    # Should not raise
    view.fit_to_scene()
