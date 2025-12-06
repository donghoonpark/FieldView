import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtCore import QObject, Signal
else:
    from qtpy.QtCore import QObject, Signal


class DataContainer(QObject):
    """
    Manages the core data (points and values) for the FieldView library.
    Emits signals when data changes.
    """

    dataChanged = Signal()

    def __init__(self):
        super().__init__()
        self._points = np.empty((0, 2), dtype=float)
        self._values = np.empty((0,), dtype=float)
        self._labels = []

    @property
    def points(self):
        return self._points

    @property
    def values(self):
        return self._values

    @property
    def labels(self):
        return self._labels

    def set_data(self, points, values, labels=None):
        """
        Sets the data points, values, and optional labels.

        Args:
            points (np.ndarray): Nx2 array of (x, y) coordinates.
            values (np.ndarray): N array of values.
            labels (list): Optional list of N strings.
        """
        points = np.array(points)
        values = np.array(values)

        if points.ndim != 2 or points.shape[1] != 2:
            raise ValueError("Points must be an Nx2 array.")
        if values.ndim != 1:
            raise ValueError("Values must be a 1D array.")
        if len(points) != len(values):
            raise ValueError("Points and values must have the same length.")

        if labels is None:
            labels = [""] * len(points)
        elif len(labels) != len(points):
            raise ValueError("Labels must have the same length as points.")

        self._points = points
        self._values = values
        self._labels = list(labels)
        self.dataChanged.emit()

    def add_points(self, points, values, labels=None):
        """
        Adds new points, values, and optional labels.
        """
        points = np.array(points)
        values = np.array(values)

        if len(points) == 0:
            return

        if labels is None:
            labels = [""] * len(points)
        elif len(labels) != len(points):
            raise ValueError("Labels must have the same length as points.")

        if self._points.shape[0] == 0:
            self.set_data(points, values, labels)
        else:
            self._points = np.vstack((self._points, points))
            self._values = np.concatenate((self._values, values))
            self._labels.extend(labels)
            self.dataChanged.emit()

    def update_point(self, index, value=None, point=None, label=None):
        """
        Updates the value, coordinate, or label of a specific point.
        """
        if index < 0 or index >= len(self._points):
            raise IndexError("Point index out of range.")

        changed = False
        if value is not None:
            self._values[index] = value
            changed = True

        if point is not None:
            self._points[index] = point
            changed = True

        if label is not None:
            self._labels[index] = label
            changed = True

        if changed:
            self.dataChanged.emit()

    def remove_points(self, indices):
        """
        Removes points at the specified indices.
        """
        if len(indices) == 0:
            return

        # Sort indices in descending order to avoid shifting issues if we were popping,
        # but numpy delete handles it. For list, we need to be careful.
        # It's better to create a mask or rebuild the list.

        mask = np.ones(len(self._points), dtype=bool)
        mask[indices] = False

        self._points = self._points[mask]
        self._values = self._values[mask]
        self._labels = [self._labels[i] for i in range(len(self._labels)) if mask[i]]

        self.dataChanged.emit()

    def clear(self):
        """
        Removes all data.
        """
        self._points = np.empty((0, 2), dtype=float)
        self._values = np.empty((0,), dtype=float)
        self._labels = []
        self.dataChanged.emit()

    def get_closest_point(self, x, y, threshold=None):
        """
        Finds the index of the closest point to (x, y).

        Args:
            x, y: Coordinates.
            threshold: Optional maximum distance. If closest point is further, returns None.

        Returns:
            int: Index of the closest point, or None.
        """
        if len(self._points) == 0:
            return None

        # Calculate squared distances
        diff = self._points - np.array([x, y])
        dist_sq = np.sum(diff**2, axis=1)

        min_idx = np.argmin(dist_sq)
        min_dist_sq = dist_sq[min_idx]

        if threshold is not None:
            if min_dist_sq > threshold**2:
                return None

        return min_idx
