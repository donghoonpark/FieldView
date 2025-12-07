import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass
else:
    pass

from fieldview.ui.field_view import FieldView
from fieldview.layers.heatmap_layer import HeatmapLayer
from fieldview.layers.pin_layer import PinLayer


def test_field_view_init(qtbot):
    view = FieldView()
    qtbot.addWidget(view)
    assert view.scene() is not None


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
