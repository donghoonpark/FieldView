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
        self._excluded_indices = set()
        
        # Connect signal
        self._data_container.dataChanged.connect(self.on_data_changed)

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
        self.update_layer()

    def get_valid_data(self):
        """
        Returns points and values excluding the excluded indices.
        """
        points = self._data_container.points
        values = self._data_container.values
        
        if not self._excluded_indices:
            return points, values
            
        # Create a mask for valid indices
        mask = [i for i in range(len(points)) if i not in self._excluded_indices]
        
        return points[mask], values[mask]
