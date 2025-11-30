import numpy as np
from scipy.interpolate import RBFInterpolator, LinearNDInterpolator
from scipy.spatial import cKDTree
from PySide6.QtGui import QImage, QPainter, QColor
from PySide6.QtCore import Qt, QTimer, QRectF

from fieldview.layers.data_layer import DataLayer

class HeatmapLayer(DataLayer):
    """
    Layer for rendering a heatmap from data points.
    Implements hybrid interpolation (Linear for speed, RBF for quality)
    and dynamic quality adjustment.
    """
    def __init__(self, data_container, parent=None):
        super().__init__(data_container, parent)
        
        # Configuration
        self._radius = 150.0 # Default radius
        self._grid_size = 300
        self._hq_delay = 300 # ms
        
        # State
        self._cached_image = None
        self._is_hq_pending = False
        
        # Timer for High Quality update
        self._hq_timer = QTimer()
        self._hq_timer.setSingleShot(True)
        self._hq_timer.setInterval(self._hq_delay)
        self._hq_timer.timeout.connect(self._perform_hq_update)
        
        # Initial update
        self.update_layer()

    @property
    def radius(self):
        return self._radius

    @radius.setter
    def radius(self, value):
        self._radius = value
        self.update_layer()

    def on_data_changed(self):
        """
        Override to trigger fast update and schedule HQ update.
        """
        # 1. Perform Fast Update (Linear)
        self._generate_heatmap(method='linear')
        self.update()
        
        # 2. Schedule High Quality Update
        self._hq_timer.start()

    def _perform_hq_update(self):
        """
        Slot for HQ timer timeout. Performs RBF interpolation.
        """
        self._generate_heatmap(method='rbf', neighbors=30)
        self.update()

    def _generate_heatmap(self, method='rbf', neighbors=30):
        """
        Generates the heatmap image.
        """
        points, values = self.get_valid_data()
        
        if len(points) < 3:
            self._cached_image = None
            return

        # 1. Generate Boundary Points (Ghost Points)
        boundary_points, boundary_values = self._generate_boundary_points(points, values)
        
        # 2. Combine Data
        all_points = np.vstack((points, boundary_points))
        all_values = np.concatenate((values, boundary_values))
        
        # 3. Create Grid
        x = np.linspace(-self._radius, self._radius, self._grid_size)
        y = np.linspace(-self._radius, self._radius, self._grid_size)
        X, Y = np.meshgrid(x, y)
        
        # 4. Interpolate
        try:
            if method == 'linear':
                interp = LinearNDInterpolator(all_points, all_values, fill_value=np.nan)
                Z = interp(X, Y)
            else: # rbf
                grid_points = np.column_stack((X.ravel(), Y.ravel()))
                interp = RBFInterpolator(all_points, all_values, neighbors=neighbors, kernel='thin_plate_spline')
                Z_flat = interp(grid_points)
                Z = Z_flat.reshape(self._grid_size, self._grid_size)
        except Exception as e:
            print(f"Interpolation failed ({method}): {e}")
            self._cached_image = None
            return

        # 5. Masking
        mask = (X**2 + Y**2) > self._radius**2
        Z[mask] = np.nan
        
        # 6. Convert to QImage
        self._cached_image = self._array_to_qimage(Z)

    def _generate_boundary_points(self, points, values):
        """
        Generates ghost points on the boundary using adaptive sampling and IDW.
        """
        if len(points) < 2:
            return np.empty((0, 2)), np.empty((0,))

        # Adaptive Sampling
        tree = cKDTree(points)
        distances, _ = tree.query(points, k=2)
        avg_dist = np.mean(distances[:, 1])
        target_segment_length = avg_dist * 1.2
        
        circumference = 2 * np.pi * self._radius
        n_boundary_points = int(np.ceil(circumference / target_segment_length))
        n_boundary_points = max(10, n_boundary_points) # Minimum points
        
        theta = np.linspace(0, 2 * np.pi, n_boundary_points, endpoint=False)
        bx = self._radius * np.cos(theta)
        by = self._radius * np.sin(theta)
        boundary_points = np.column_stack((bx, by))
        
        # IDW for Values
        dists, indices = tree.query(boundary_points, k=2)
        boundary_values = []
        
        for i in range(len(boundary_points)):
            d1, d2 = dists[i]
            idx1, idx2 = indices[i]
            v1, v2 = values[idx1], values[idx2]
            
            if d1 < 1e-9: val = v1
            elif d2 < 1e-9: val = v2
            else:
                w1 = 1.0 / d1
                w2 = 1.0 / d2
                val = (w1 * v1 + w2 * v2) / (w1 + w2)
            boundary_values.append(val)
            
        return boundary_points, np.array(boundary_values)

    def _array_to_qimage(self, Z):
        """
        Converts 2D array Z to QImage.
        """
        height, width = Z.shape
        image = QImage(width, height, QImage.Format.Format_ARGB32)
        
        Z_norm = np.nan_to_num(Z, nan=-1)
        max_val = np.nanmax(Z_norm)
        if max_val == 0: max_val = 1
        
        # This is slow in Python, but fine for POC. 
        # In production, use numpy-to-bytes conversion.
        for y in range(height):
            for x in range(width):
                val = Z_norm[y, x]
                if val == -1:
                    color = QColor(0, 0, 0, 0)
                else:
                    ratio = max(0.0, min(1.0, val / max_val))
                    r = int(255 * ratio)
                    b = int(255 * (1 - ratio))
                    color = QColor(r, 0, b, 255)
                image.setPixelColor(x, y, color)
                
        return image

    def paint(self, painter, option, widget):
        if self._cached_image:
            # Draw image centered in the bounding rect
            # Assuming bounding rect is centered at 0,0 and size is 2*radius
            target_rect = QRectF(-self._radius, -self._radius, self._radius * 2, self._radius * 2)
            painter.drawImage(target_rect, self._cached_image)
