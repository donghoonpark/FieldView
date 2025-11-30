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
    renderingFinished = Signal(float, int) # Duration in ms, Grid Size

    def __init__(self, data_container, parent=None):
        super().__init__(data_container, parent)
        
        # Configuration
        self._boundary_shape = QPolygonF() # Default empty
        self._auto_boundary = True # Default to auto-fit data
        self._grid_size = 50 # Start low for fast initial render
        self._neighbors = 30
        self._target_render_time = 100 # Default High (100ms)
        self._hq_delay = 300 # ms
        self._colormap = get_colormap("viridis")
        
        # Initialize with empty shape, will be set by on_data_changed if data exists
        # or user can set it manually.
        
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

    @property
    def target_render_time(self):
        return self._target_render_time

    @target_render_time.setter
    def target_render_time(self, ms):
        self._target_render_time = float(ms)
        # Trigger update to adapt immediately
        self.on_data_changed()

    @property
    def quality(self):
        # Backward compatibility / UI helper
        if self._target_render_time <= 20: return 'low'
        if self._target_render_time <= 50: return 'medium'
        return 'high'

    @quality.setter
    def quality(self, value):
        if isinstance(value, str):
            value = value.lower()
        
        if value in ['low', 0]:
            self.target_render_time = 20
        elif value in ['medium', 1]:
            self.target_render_time = 50
        elif value in ['high', 2]:
            self.target_render_time = 100
        else:
            print(f"Warning: Invalid quality '{value}'. Ignoring.")

    def set_boundary_shape(self, shape):
        """
        Sets the boundary polygon for the heatmap.
        Accepts QPolygonF, QRectF, or QPainterPath.
        Disables auto-boundary mode.
        """
        self._auto_boundary = False
        
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

        # Auto-boundary logic
        if self._auto_boundary:
            points, _, _ = self.get_valid_data()
            if len(points) > 0:
                min_x = np.min(points[:, 0])
                max_x = np.max(points[:, 0])
                min_y = np.min(points[:, 1])
                max_y = np.max(points[:, 1])
                
                # Add some padding (e.g. 10%)
                width = max_x - min_x
                height = max_y - min_y
                padding_x = max(10, width * 0.1)
                padding_y = max(10, height * 0.1)
                
                rect = QRectF(min_x - padding_x, min_y - padding_y, 
                              width + 2*padding_x, height + 2*padding_y)
                self._boundary_shape = QPolygonF(rect)
                self.set_bounding_rect(rect)
            else:
                self._boundary_shape = QPolygonF()
                self.set_bounding_rect(QRectF())

        # 1. Cancel any pending HQ update
        if hasattr(self, '_hq_timer'):
            self._hq_timer.stop()
        
        # 2. Perform Fast Update (Low-Res RBF)
        # Use 1/10th of the grid size for speed (e.g., 30x30 instead of 300x300)
        low_res_size = max(10, int(self._grid_size / 1.6))
        self._generate_heatmap(method='rbf', neighbors=self._neighbors, grid_size=low_res_size)
        self.update()
        
        # 3. Schedule High Quality Update
        if hasattr(self, '_hq_timer'):
            self._hq_timer.start()

    def _perform_hq_update(self):
        """
        Slot for HQ timer timeout. Performs RBF interpolation.
        """
        self._generate_heatmap(method='rbf', neighbors=self._neighbors, grid_size=self._grid_size)
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

        # print(f"Total: {duration_ms:.1f}ms | Boundary: {(t1-t0)*1000:.1f}ms | Interp: {(t3-t2)*1000:.1f}ms | Image: {(t4-t3)*1000:.1f}ms")
        
        self.renderingFinished.emit(duration_ms, grid_size)

        # 7. Adaptive Quality Adjustment
        if self._target_render_time > 0 and duration_ms > 0:
            # Calculate target grid size
            # Time is roughly proportional to grid_size^2 (number of evaluation points)
            # target_time / current_time = target_grid^2 / current_grid^2
            # target_grid = current_grid * sqrt(target_time / current_time)
            
            ratio = self._target_render_time / duration_ms
            # Clamp ratio to prevent wild swings (e.g., 0.5x to 2.0x)
            ratio = max(0.5, min(2.0, ratio))
            
            new_grid_size = int(grid_size * np.sqrt(ratio))
            
            # Clamp grid size
            new_grid_size = max(30, min(500, new_grid_size))
            
            # Apply smoothing (EMA)
            alpha = 0.3
            self._grid_size = int(alpha * new_grid_size + (1 - alpha) * self._grid_size)
            

            print(f"Render: {duration_ms:.1f}ms, Target: {self._target_render_time}ms, Ratio {ratio:.2f} New Grid: {self._grid_size}")

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
        Converts 2D array Z to QImage using vectorized operations.
        """
        height, width = Z.shape
        
        # 1. Normalize Z to 0-255 indices
        Z_norm = np.nan_to_num(Z, nan=-1)
        max_val = np.nanmax(Z_norm)
        if max_val == 0: max_val = 1
        
        # Create indices array
        # Values < 0 (NaNs) will be handled separately or mapped to 0
        # We want -1 to stay -1 or be handled. 
        # Let's map valid values to 0-255.
        
        # Mask for transparent pixels
        mask = (Z_norm == -1)
        
        # Normalize valid values to 0.0-1.0
        normalized = np.clip(Z_norm / max_val, 0.0, 1.0)
        
        # Map to 0-255 indices
        indices = (normalized * 255).astype(np.uint8)
        
        # 2. Get LUT
        lut = self._colormap.get_lut(256)
        
        # 3. Map indices to ARGB values
        # lut is (256,) uint32
        # buffer will be (height, width) uint32
        buffer = lut[indices]
        
        # 4. Apply Transparency
        # Set alpha to 0 for masked pixels
        # 0x00FFFFFF mask clears Alpha channel, but we want 0x00000000 for full transparency
        buffer[mask] = 0x00000000
        
        # 5. Create QImage from buffer
        # We need to ensure the buffer is contiguous and kept alive
        # QImage(uchar *data, int width, int height, Format format)
        # We can use memoryview
        
        # Make sure buffer is C-contiguous
        if not buffer.flags['C_CONTIGUOUS']:
            buffer = np.ascontiguousarray(buffer)
            
        image = QImage(buffer.data, width, height, width * 4, QImage.Format.Format_ARGB32)
        
        # We must copy the image data because QImage doesn't own the buffer
        # and 'buffer' might be garbage collected after this function returns.
        return image.copy()

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

