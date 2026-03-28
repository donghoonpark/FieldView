from fieldview.core.data_container import DataContainer
from fieldview.layers.data_layer import DataLayer


def test_datalayer_initialization(qtbot):
    dc = DataContainer()
    layer = DataLayer(dc)
    assert layer.data_container == dc
    assert len(layer.excluded_indices) == 0


def test_datalayer_update_on_data_change(qtbot, monkeypatch):
    dc = DataContainer()
    layer = DataLayer(dc)

    # Mock update_layer to verify it's called
    called = False

    def mock_update():
        nonlocal called
        called = True

    monkeypatch.setattr(layer, "update_layer", mock_update)

    dc.set_data([[0, 0]], [10])
    assert called


def test_excluded_indices():
    dc = DataContainer()
    dc.set_data([[0, 0], [1, 1], [2, 2]], [10, 20, 30], ["A", "B", "C"])
    layer = DataLayer(dc)

    layer.set_excluded_indices([1])
    assert layer.excluded_indices == {1}

    points, values, labels = layer.get_valid_data()
    assert len(points) == 2
    assert values[0] == 10
    assert values[1] == 30
    assert labels[0] == "A"
    assert labels[1] == "C"


def test_add_remove_excluded_index():
    dc = DataContainer()
    layer = DataLayer(dc)

    layer.add_excluded_index(5)
    assert 5 in layer.excluded_indices

    layer.remove_excluded_index(5)
    assert 5 not in layer.excluded_indices


def test_empty_data_resets_bounding_rect():
    dc = DataContainer()
    layer = DataLayer(dc)

    dc.set_data([[0, 0], [10, 10]], [1, 2])
    assert layer.boundingRect().width() > 0

    dc.clear()
    rect = layer.boundingRect()
    assert rect.width() == 0
    assert rect.height() == 0


def test_excluded_indices_update_bounding_rect():
    dc = DataContainer()
    dc.set_data([[0, 0], [100, 100]], [1, 2])
    layer = DataLayer(dc)

    full_rect = layer.boundingRect()
    layer.set_excluded_indices([1])
    filtered_rect = layer.boundingRect()

    assert filtered_rect.width() < full_rect.width()
    assert filtered_rect.height() < full_rect.height()
