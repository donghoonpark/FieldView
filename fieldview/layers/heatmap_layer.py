import numpy as np
import time
from scipy.interpolate import RBFInterpolator, LinearNDInterpolator
from scipy.spatial import cKDTree
from PySide6.QtGui import QImage, QPainter, QColor, QPolygonF, QPainterPath
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, Signal

from fieldview.layers.data_layer import DataLayer

from fieldview.rendering.colormaps import get_colormap

class HeatmapLayer(DataLayer):
    """
    Layer for rendering a heatmap from data points.
    Implements hybrid interpolation (Linear for speed, RBF for quality)
    and dynamic quality adjustment.
    Supports arbitrary polygon boundaries.
    """
    renderingFinished = Signal(float) # Duration in ms

    def __init__(self, data_container, parent=None):
        super().__init__(data_container, parent)
        
        # Configuration
        self._boundary_shape = QPolygonF() # Default empty
        self._grid_size = 300
        self._hq_delay = 300 # ms
        self._colormap = get_colormap("viridis")
        
        # Initialize with a default square shape
        self.set_boundary_shape(QPolygonF([
            QPointF(-150, -150), QPointF(150, -150),
            QPointF(150, 150), QPointF(-150, 150)
        ]))
        
        # State
        self._cached_image = None
        self._heatmap_rect = QRectF()
        self._is_hq_pending = False
        
        # Timer for High Quality update
        self._hq_timer = QTimer()
        self._hq_timer.setSingleShot(True)
        self._hq_timer.setInterval(self._hq_delay)
        self._hq_timer.timeout.connect(self._perform_hq_update)
        
        # Initial update
        self.on_data_changed()

    @property
    def colormap(self):
        return self._colormap.name

    @colormap.setter
    def colormap(self, name):
        self._colormap = get_colormap(name)
        self.update_layer()

    def set_boundary_shape(self, shape):
        """
        Sets the boundary polygon for the heatmap.
        Accepts QPolygonF, QRectF, or QPainterPath.
        """
        if isinstance(shape, QRectF):
            self._boundary_shape = QPolygonF(shape)
        elif isinstance(shape, QPainterPath):
            self._boundary_shape = shape.toFillPolygon()
        elif isinstance(shape, QPolygonF):
            self._boundary_shape = shape
        else:
            raise TypeError("Shape must be QPolygonF, QRectF, or QPainterPath")

        self.set_bounding_rect(self._boundary_shape.boundingRect())
        # Trigger update to regenerate heatmap with new boundary
        self.on_data_changed()

    def on_data_changed(self):
        """
        Override to trigger fast update and schedule HQ update.
        """
        # Check if initialized
        if not hasattr(self, '_grid_size'):
            return

        # 1. Cancel any pending HQ update
        if hasattr(self, '_hq_timer'):
            self._hq_timer.stop()
        
        # 2. Perform Fast Update (Low-Res RBF)
        # Use 1/10th of the grid size for speed (e.g., 30x30 instead of 300x300)
        low_res_size = max(10, self._grid_size // 10)
        self._generate_heatmap(method='rbf', neighbors=30, grid_size=low_res_size)
        self.update()
        
        # 3. Schedule High Quality Update
        if hasattr(self, '_hq_timer'):
            self._hq_timer.start()

    def _perform_hq_update(self):
        """
        Slot for HQ timer timeout. Performs RBF interpolation.
        """
        self._generate_heatmap(method='rbf', neighbors=30, grid_size=self._grid_size)
        self.update()

    def _generate_heatmap(self, method='rbf', neighbors=30, grid_size=None):
        """
        Generates the heatmap image.
        """
        start_time = time.perf_counter()

        if grid_size is None:
            grid_size = self._grid_size

        points, values, _ = self.get_valid_data()
        
        if len(points) < 3 or self._boundary_shape.isEmpty():
            self._cached_image = None
            return

        # 1. Generate Boundary Points (Ghost Points)
        boundary_points, boundary_values = self._generate_boundary_points(points, values)
        
        # 2. Combine Data
        all_points = np.vstack((points, boundary_points))
        all_values = np.concatenate((values, boundary_values))
        
        # 3. Create Grid based on Bounding Rect
        # We expand the grid by 1 unit on all sides to avoid edge artifacts
        rect = self._boundary_shape.boundingRect()
        
        # Calculate pixel size
        dx = rect.width() / grid_size
        dy = rect.height() / grid_size
        
        # Expand rect by 1 pixel size on all sides
        expanded_rect = rect.adjusted(-dx, -dy, dx, dy)
        self._heatmap_rect = expanded_rect
        
        # Update grid size to cover the expanded area
        # We added 2 units of width/height (1 on each side)
        expanded_grid_size = grid_size + 2
        
        x = np.linspace(expanded_rect.left(), expanded_rect.right(), expanded_grid_size)
        y = np.linspace(expanded_rect.top(), expanded_rect.bottom(), expanded_grid_size)
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
                Z = Z_flat.reshape(expanded_grid_size, expanded_grid_size)
        except Exception as e:
            print(f"Interpolation failed ({method}): {e}")
            self._cached_image = None
            return

        # 5. Masking - REMOVED
        # We rely on QPainter clipping in paint() for precise masking.
        # This avoids the loop and ensures clean edges.
        
        # 6. Convert to QImage
        self._cached_image = self._array_to_qimage(Z)
        
        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000
        self.renderingFinished.emit(duration_ms)

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
        if target_segment_length <= 0: target_segment_length = 10.0
        
        boundary_points_list = []
        
        # Iterate through polygon edges
        poly_points = [self._boundary_shape.at(i) for i in range(self._boundary_shape.count())]
        if self._boundary_shape.isClosed():
             # QPolygonF might be closed or not depending on creation. 
             # If last point != first point, close it effectively for iteration
             if poly_points[0] != poly_points[-1]:
                 poly_points.append(poly_points[0])
        else:
             poly_points.append(poly_points[0]) # Close the loop
             
        for i in range(len(poly_points) - 1):
            p1 = np.array([poly_points[i].x(), poly_points[i].y()])
            p2 = np.array([poly_points[i+1].x(), poly_points[i+1].y()])
            
            segment_len = np.linalg.norm(p2 - p1)
            n_segments = int(np.ceil(segment_len / target_segment_length))
            n_segments = max(1, n_segments)
            
            for j in range(n_segments):
                t = j / n_segments
                pt = p1 + t * (p2 - p1)
                boundary_points_list.append(pt)
                
        boundary_points = np.array(boundary_points_list)
        
        if len(boundary_points) == 0:
             return np.empty((0, 2)), np.empty((0,))

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
        image.fill(Qt.GlobalColor.transparent) # Initialize with transparent
        
        Z_norm = np.nan_to_num(Z, nan=-1)
        max_val = np.nanmax(Z_norm)
        if max_val == 0: max_val = 1
        
        for y in range(height):
            for x in range(width):
                val = Z_norm[y, x]
                if val == -1:
                    continue # Already transparent
                else:
                    ratio = max(0.0, min(1.0, val / max_val))
                    color = self._colormap.map(ratio)
                    # Apply opacity if needed, but QGraphicsObject handles global opacity.
                    # We just set alpha to 255 here.
                    color.setAlpha(255)
                    image.setPixelColor(x, y, color)
                
        return image

    def paint(self, painter, option, widget):
        if self._cached_image:
            # Clip to polygon
            path = QPainterPath()
            path.addPolygon(self._boundary_shape)
            painter.setClipPath(path)
            
            # Draw the expanded heatmap
            # Enable smooth transformation for upscaling low-res images
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            painter.drawImage(self._heatmap_rect, self._cached_image)

