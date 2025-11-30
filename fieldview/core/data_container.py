import numpy as np
from PySide6.QtCore import QObject, Signal

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

    @property
    def points(self):
        return self._points

    @property
    def values(self):
        return self._values

    def set_data(self, points, values):
        """
        Sets the data points and values.
        
        Args:
            points (np.ndarray): Nx2 array of (x, y) coordinates.
            values (np.ndarray): N array of values.
        """
        points = np.array(points)
        values = np.array(values)

        if points.ndim != 2 or points.shape[1] != 2:
            raise ValueError("Points must be an Nx2 array.")
        if values.ndim != 1:
            raise ValueError("Values must be a 1D array.")
        if len(points) != len(values):
            raise ValueError("Points and values must have the same length.")

        self._points = points
        self._values = values
        self.dataChanged.emit()

    def add_points(self, points, values):
        """
        Adds new points and values to the existing data.
        """
        points = np.array(points)
        values = np.array(values)
        
        if len(points) == 0:
            return

        if self._points.shape[0] == 0:
            self.set_data(points, values)
        else:
            self._points = np.vstack((self._points, points))
            self._values = np.concatenate((self._values, values))
            self.dataChanged.emit()

    def update_point(self, index, value=None, point=None):
        """
        Updates the value or coordinate of a specific point.
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
            
        if changed:
            self.dataChanged.emit()

    def remove_points(self, indices):
        """
        Removes points at the specified indices.
        """
        if len(indices) == 0:
            return
            
        self._points = np.delete(self._points, indices, axis=0)
        self._values = np.delete(self._values, indices)
        self.dataChanged.emit()

    def clear(self):
        """
        Removes all data.
        """
        self._points = np.empty((0, 2), dtype=float)
        self._values = np.empty((0,), dtype=float)
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
