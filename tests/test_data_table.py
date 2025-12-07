import pytest
import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtCore import Qt
else:
    from qtpy.QtCore import Qt

from fieldview.core.data_container import DataContainer
from fieldview.ui.data_table import PointTableModel, DataTable, CHECKED, UNCHECKED


@pytest.fixture
def data_container():
    dc = DataContainer()
    points = np.array([[10, 20], [30, 40], [50, 60]])
    values = np.array([1.0, 2.0, 3.0])
    labels = ["A", "B", "C"]
    dc.set_data(points, values, labels)
    return dc


def test_model_row_column_count(data_container):
    model = PointTableModel(data_container)
    assert model.rowCount() == 3
    assert model.columnCount() == 6


def test_model_data_display_role(data_container):
    model = PointTableModel(data_container)
    # Col 2 is X, Col 3 is Y, Col 4 is Value, Col 5 is Label
    index_x = model.index(0, 2)
    assert model.data(index_x, Qt.ItemDataRole.DisplayRole) == "10.00"

    index_val = model.index(1, 4)
    assert model.data(index_val, Qt.ItemDataRole.DisplayRole) == "2.00"

    index_label = model.index(2, 5)
    assert model.data(index_label, Qt.ItemDataRole.DisplayRole) == "C"


def test_model_data_check_state_role(data_container):
    model = PointTableModel(data_container)
    # Col 0 is Highlight, Col 1 is Exclude
    index_highlight = model.index(0, 0)
    assert (
        model.data(index_highlight, Qt.ItemDataRole.CheckStateRole)
        == Qt.CheckState.Unchecked
    )

    # Manually add to highlighted set to verify
    model._highlighted_indices.add(0)
    assert (
        model.data(index_highlight, Qt.ItemDataRole.CheckStateRole)
        == Qt.CheckState.Checked
    )


def test_model_set_data_edit(data_container):
    model = PointTableModel(data_container)
    index_val = model.index(0, 4)

    # Update value
    assert model.setData(index_val, "99.9", Qt.ItemDataRole.EditRole)
    assert data_container.values[0] == 99.9

    # Verify dataChanged signal (optional, but good practice)
    # Here we just check the underlying data updated


def test_model_set_data_check_state(data_container):
    model = PointTableModel(data_container)
    index_exclude = model.index(0, 1)

    # Check
    assert model.setData(index_exclude, CHECKED, Qt.ItemDataRole.CheckStateRole)
    assert 0 in model._excluded_indices

    # Uncheck
    assert model.setData(index_exclude, UNCHECKED, Qt.ItemDataRole.CheckStateRole)
    assert 0 not in model._excluded_indices


def test_model_flags(data_container):
    model = PointTableModel(data_container)

    # Checkable column
    index_check = model.index(0, 0)
    flags = model.flags(index_check)
    assert flags & Qt.ItemFlag.ItemIsUserCheckable

    # Editable column
    index_edit = model.index(0, 2)
    flags = model.flags(index_edit)
    assert flags & Qt.ItemFlag.ItemIsEditable


def test_data_table_init(qtbot, data_container):
    table = DataTable(data_container)
    qtbot.addWidget(table)
    assert table.model() is not None
    assert isinstance(table.table_model, PointTableModel)
