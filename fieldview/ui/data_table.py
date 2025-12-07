from qtpy.QtWidgets import QTableView, QHeaderView, QMenu, QAction
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtCore import (
        Qt,
        QAbstractTableModel,
        QModelIndex,
        QPersistentModelIndex,
    )
else:
    from qtpy.QtCore import Qt, QAbstractTableModel, QModelIndex, QPersistentModelIndex
from typing import List, Set, Any, Union
from fieldview.core.data_container import DataContainer


# Cross-binding compatibility for CheckState
try:
    CHECKED = Qt.CheckState.Checked.value
    UNCHECKED = Qt.CheckState.Unchecked.value
except AttributeError:
    CHECKED = int(Qt.CheckState.Checked)  # type: ignore
    UNCHECKED = int(Qt.CheckState.Unchecked)  # type: ignore


class PointTableModel(QAbstractTableModel):
    """
    Table model for DataContainer points.
    Supports editing and column visibility toggling.
    """

    def __init__(self, data_container: DataContainer):
        super().__init__()
        self._data_container = data_container
        self._data_container.dataChanged.connect(self._handle_data_changed)
        self._highlighted_indices: Set[int] = set()
        self._excluded_indices: Set[int] = set()

        self._headers = ["Highlight", "Exclude", "X", "Y", "Value", "Label"]
        self._visible_columns = [True] * len(self._headers)

    def rowCount(
        self, parent: Union["QModelIndex", "QPersistentModelIndex"] = QModelIndex()
    ) -> int:
        return len(self._data_container.points)

    def columnCount(
        self, parent: Union["QModelIndex", "QPersistentModelIndex"] = QModelIndex()
    ) -> int:
        return len(self._headers)

    def data(
        self,
        index: Union["QModelIndex", "QPersistentModelIndex"],
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if not index.isValid():
            return None
        row, col = index.row(), index.column()

        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            if col == 2:
                return f"{self._data_container.points[row][0]:.2f}"
            if col == 3:
                return f"{self._data_container.points[row][1]:.2f}"
            if col == 4:
                return f"{self._data_container.values[row]:.2f}"
            if col == 5:
                return self._data_container.labels[row]

        if role == Qt.ItemDataRole.CheckStateRole:
            if col == 0:
                return (
                    Qt.CheckState.Checked
                    if row in self._highlighted_indices
                    else Qt.CheckState.Unchecked
                )
            if col == 1:
                return (
                    Qt.CheckState.Checked
                    if row in self._excluded_indices
                    else Qt.CheckState.Unchecked
                )
        return None

    def setData(
        self,
        index: Union["QModelIndex", "QPersistentModelIndex"],
        value: Any,
        role: int = Qt.ItemDataRole.EditRole,
    ) -> bool:
        if not index.isValid():
            return False
        row, col = index.row(), index.column()

        if role == Qt.ItemDataRole.CheckStateRole:
            if col == 0:
                if value == CHECKED:
                    self._highlighted_indices.add(row)
                else:
                    self._highlighted_indices.discard(row)
            elif col == 1:
                if value == CHECKED:
                    self._excluded_indices.add(row)
                else:
                    self._excluded_indices.discard(row)
            else:
                return False
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.CheckStateRole])
            return True

        if role == Qt.ItemDataRole.EditRole:
            try:
                if col == 2:
                    new_x = float(value)
                    y = self._data_container.points[row][1]
                    self._data_container.update_point(row, point=[new_x, y])
                elif col == 3:
                    new_y = float(value)
                    x = self._data_container.points[row][0]
                    self._data_container.update_point(row, point=[x, new_y])
                elif col == 4:
                    new_val = float(value)
                    self._data_container.update_point(row, value=new_val)
                elif col == 5:
                    self._data_container.update_point(row, label=str(value))
                return True
            except ValueError:
                return False
        return False

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if (
            role == Qt.ItemDataRole.DisplayRole
            and orientation == Qt.Orientation.Horizontal
        ):
            return self._headers[section]
        return None

    def flags(
        self, index: Union["QModelIndex", "QPersistentModelIndex"]
    ) -> Qt.ItemFlag:
        flags = super().flags(index)
        if index.column() in (0, 1):
            flags |= Qt.ItemFlag.ItemIsUserCheckable
        else:
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    def get_highlighted_indices(self) -> List[int]:
        return list(self._highlighted_indices)

    def get_excluded_indices(self) -> List[int]:
        return list(self._excluded_indices)

    def _handle_data_changed(self):
        self.layoutChanged.emit()


class DataTable(QTableView):
    """
    Custom TableView with context menu for column visibility.
    """

    def __init__(self, data_container: DataContainer, parent=None):
        super().__init__(parent)
        self._model = PointTableModel(data_container)
        self.setModel(self._model)

        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.horizontalHeader().customContextMenuRequested.connect(
            self._show_header_menu
        )

        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)

    def _show_header_menu(self, pos):
        menu = QMenu(self)
        header = self.horizontalHeader()

        for i in range(self._model.columnCount()):
            col_name = self._model.headerData(i, Qt.Orientation.Horizontal)
            action = QAction(col_name, menu)
            action.setCheckable(True)
            action.setChecked(not header.isSectionHidden(i))
            action.setData(i)
            action.triggered.connect(self._toggle_column)
            menu.addAction(action)

        menu.exec(header.mapToGlobal(pos))

    def _toggle_column(self):
        action: QAction = self.sender()  # type: ignore
        col_idx = action.data()
        if action.isChecked():
            self.showColumn(col_idx)
        else:
            self.hideColumn(col_idx)

    @property
    def table_model(self) -> PointTableModel:
        return self._model
