from fieldview.ui import ColorRangeControl


def test_color_range_control_spinboxes(qtbot):
    widget = ColorRangeControl(colormap_name="magma")
    qtbot.addWidget(widget)

    # Increasing the minimum past the maximum clamps the max to match
    with qtbot.waitSignal(widget.colorRangeChanged) as changed:
        widget._min_spin.setValue(2.5)
    assert changed.args == [2.5, 2.5]

    # Raising the max keeps ordering intact
    with qtbot.waitSignal(widget.colorRangeChanged) as changed:
        widget._max_spin.setValue(10.0)
    assert changed.args == [2.5, 10.0]

    # set_range can silence emissions and pushes values into the spinboxes
    widget.set_range(1.0, 3.0, emit_signal=False)
    assert widget.minimum_value == 1.0
    assert widget.maximum_value == 3.0

    # Lowering the max below the min clamps the min down as well
    with qtbot.waitSignal(widget.colorRangeChanged) as changed:
        widget._max_spin.setValue(0.5)
    assert changed.args == [0.5, 0.5]


def test_color_range_control_colormap_updates(qtbot):
    widget = ColorRangeControl()
    qtbot.addWidget(widget)

    widget.set_colormap("inferno")
    assert widget.colorbar.colormap_name == "inferno"
