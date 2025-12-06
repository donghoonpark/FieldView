from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtCore import QRectF
else:
    from qtpy.QtCore import QRectF
import numpy as np
from fieldview.layers.layer import Layer
from fieldview.core.data_container import DataContainer


class DataLayer(Layer):
    """
    Base class for layers that visualize data from a DataContainer.
    Handles data change signals and excluded indices.
    """

    def __init__(self, data_container: DataContainer, parent=None):
        super().__init__(parent)
        self._data_container = data_container
        self._excluded_indices: set[int] = set()

        # Connect signal
        self._data_container.dataChanged.connect(self.on_data_changed)
        # Initial update
        self.on_data_changed()

    @property
    def data_container(self):
        return self._data_container

    @property
    def excluded_indices(self):
        return self._excluded_indices

    def set_excluded_indices(self, indices):
        """
        Sets the set of indices to exclude from visualization.
        """
        self._excluded_indices = set(indices)
        self.update_layer()

    def add_excluded_index(self, index):
        self._excluded_indices.add(index)
        self.update_layer()

    def remove_excluded_index(self, index):
        if index in self._excluded_indices:
            self._excluded_indices.remove(index)
            self.update_layer()

    def clear_excluded_indices(self):
        self._excluded_indices.clear()
        self.update_layer()

    def on_data_changed(self):
        """
        Slot called when DataContainer data changes.
        """
        self._update_bounding_rect()
        self.update_layer()

    def get_valid_indices(self):
        """
        Returns the list of data-container indices that are not excluded.
        """
        if not self._excluded_indices:
            return list(range(len(self._data_container.points)))
        return [
            i
            for i in range(len(self._data_container.points))
            if i not in self._excluded_indices
        ]

    def _update_bounding_rect(self):
        points = self._data_container.points
        if len(points) == 0:
            return

        min_x = np.min(points[:, 0])
        max_x = np.max(points[:, 0])
        min_y = np.min(points[:, 1])
        max_y = np.max(points[:, 1])

        # Add padding (e.g., for icons or text)
        padding = 50
        rect = QRectF(
            min_x - padding,
            min_y - padding,
            max_x - min_x + 2 * padding,
            max_y - min_y + 2 * padding,
        )
        self.set_bounding_rect(rect)

    def get_valid_data(self):
        """
        Returns points, values, and labels excluding the excluded indices.
        """
        points = self._data_container.points
        values = self._data_container.values
        labels = self._data_container.labels

        if not self._excluded_indices:
            return points, values, labels

        # Create a mask for valid indices
        mask = self.get_valid_indices()

        # Filter labels (list)
        valid_labels = [labels[i] for i in mask]

        return points[mask], values[mask], valid_labels
