import numpy as np
import time
from fieldview.utils.interpolation import FastRBFInterpolator, BoundaryPointGenerator
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
        
        # Interpolators
        self._boundary_gen = BoundaryPointGenerator()
        self._rbf_interp = FastRBFInterpolator(neighbors=self._neighbors)
        
        # Cache Keys
        self._last_points_hash = None
        self._last_boundary_hash = None
        self._last_grid_size = None
        
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
        Generates the heatmap image using cached interpolators.
        """
        start_time = time.perf_counter()

        if grid_size is None:
            grid_size = self._grid_size

        points, values, _ = self.get_valid_data()

        if len(points) < 3 or self._boundary_shape.isEmpty():
            self._cached_image = None
            return

        # Check if geometry changed (Points location or Boundary or Grid Size)
        # We use a simple hash of points coordinates for check
        points_hash = hash(points.tobytes())
        # Boundary hash is tricky, let's use boundingRect for now or just assume it changes less often
        # Actually, let's just use the point count and first point as a cheap hash for boundary
        boundary_hash = (self._boundary_shape.count(), self._boundary_shape.at(0).x() if not self._boundary_shape.isEmpty() else 0)
        
        geometry_changed = (
            points_hash != self._last_points_hash or 
            boundary_hash != self._last_boundary_hash or
            grid_size != self._last_grid_size
        )

        if geometry_changed:
            # 1. Fit Boundary Generator
            self._boundary_gen.fit(points, self._boundary_shape)
            
            # 2. Get Boundary Points
            boundary_points = self._boundary_gen.get_boundary_points()
            
            # 3. Combine Points for RBF Fit
            if len(boundary_points) > 0:
                all_source_points = np.vstack((points, boundary_points))
            else:
                all_source_points = points
                
            # 4. Create Grid
            rect = self._boundary_shape.boundingRect()
            dx = rect.width() / grid_size
            dy = rect.height() / grid_size
            expanded_rect = rect.adjusted(-dx, -dy, dx, dy)
            self._heatmap_rect = expanded_rect
            expanded_grid_size = grid_size + 2
            
            x = np.linspace(expanded_rect.left(), expanded_rect.right(), expanded_grid_size)
            y = np.linspace(expanded_rect.top(), expanded_rect.bottom(), expanded_grid_size)
            X, Y = np.meshgrid(x, y)
            grid_points = np.column_stack((X.ravel(), Y.ravel()))
            
            # 5. Fit Fast RBF
            # Update neighbors if needed
            self._rbf_interp.neighbors = neighbors
            self._rbf_interp.fit(all_source_points, grid_points)
            
            # Update Cache Keys
            self._last_points_hash = points_hash
            self._last_boundary_hash = boundary_hash
            self._last_grid_size = grid_size
            
            # Store grid shape for reshaping later
            self._last_grid_shape = (expanded_grid_size, expanded_grid_size)

        # --- Fast Update Phase (Values Only) ---
        
        # 1. Get Boundary Values
        boundary_values = self._boundary_gen.transform(values)
        
        # 2. Combine Values
        if len(boundary_values) > 0:
            all_values = np.concatenate((values, boundary_values))
        else:
            all_values = values
            
        # 3. Predict
        Z_flat = self._rbf_interp.predict(all_values)
        
        if Z_flat is None:
            self._cached_image = None
            return
            
        Z = Z_flat.reshape(self._last_grid_shape)

        # 4. Convert to QImage
        self._cached_image = self._array_to_qimage(Z)

        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000

        self.renderingFinished.emit(duration_ms, grid_size)

        # 5. Adaptive Quality Adjustment
        if self._target_render_time > 0 and duration_ms > 0:
            ratio = self._target_render_time / duration_ms
            ratio = max(0.5, min(2.0, ratio))
            new_grid_size = int(grid_size * np.sqrt(ratio))
            new_grid_size = max(30, min(500, new_grid_size))
            alpha = 0.3
            self._grid_size = int(alpha * new_grid_size + (1 - alpha) * self._grid_size)
            # print(f"Render: {duration_ms:.1f}ms, Target: {self._target_render_time}ms, Ratio {ratio:.2f} New Grid: {self._grid_size}")



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

