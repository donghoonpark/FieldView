import numpy as np
import time
from fieldview.utils.grid_manager import InterpolatorCache
from typing import TYPE_CHECKING, Optional, Literal, Union

if TYPE_CHECKING:
    from PySide6.QtGui import QImage, QPainter, QPolygonF, QPainterPath
    from PySide6.QtCore import QTimer, QRectF, Signal
    from PySide6.QtWidgets import QStyleOptionGraphicsItem, QWidget
else:
    from qtpy.QtGui import QImage, QPainter, QPolygonF, QPainterPath
    from qtpy.QtCore import QTimer, QRectF, Signal
    from qtpy.QtWidgets import QStyleOptionGraphicsItem, QWidget

from fieldview.rendering.colormaps import ColormapName, get_colormap
from fieldview.layers.data_layer import DataLayer

QualityLevel = Literal["very low", "low", "medium", "high", "very high", "adaptive"]
KernelType = Literal[
    "thin_plate_spline",
    "linear",
    "cubic",
    "quintic",
    "gaussian",
    "multiquadric",
    "inverse_multiquadric",
    "",
]


# Tiered grid sizes to prevent cache thrashing
TIERS = [50, 100, 150, 200, 250, 300, 400, 500]


class HeatmapLayer(DataLayer):
    """
    Layer for rendering a heatmap from data points.
    Implements hybrid interpolation (Linear for speed, RBF for quality)
    and dynamic quality adjustment.
    Supports arbitrary polygon boundaries.
    """

    renderingFinished = Signal(float, int)  # Duration in ms, Grid Size

    def __init__(self, data_container, parent=None):
        super().__init__(data_container, parent)

        # Configuration
        self._boundary_shape = QPolygonF()  # Default empty
        self._auto_boundary = True  # Default to auto-fit data
        self._preview_grid_size = 50  # Fast update size
        self._idle_grid_size = 150  # HQ update size
        self._is_adaptive = False
        self._neighbors = 30
        self._target_render_time = 100.0  # Default High (100ms)
        self._hq_delay = 300  # ms
        self._colormap = get_colormap("viridis")
        self._kernel: KernelType = "thin_plate_spline"
        self._color_min = None
        self._color_max = None

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
        self._interpolator_cache = InterpolatorCache()

        # Cache Keys
        self._last_grid_shape = None

        # Initial update
        self.on_data_changed()

    @property
    def colormap(self) -> str:
        return self._colormap.name

    @colormap.setter
    def colormap(self, name: Union[ColormapName, str]):
        self._colormap = get_colormap(name)
        self.update_layer()

    @property
    def color_min(self):
        return self._color_min

    @property
    def color_max(self):
        return self._color_max

    @property
    def color_range(self):
        return self._color_min, self._color_max

    def set_color_range(
        self, color_min: Optional[float] = None, color_max: Optional[float] = None
    ):
        """
        Sets explicit normalization bounds for the heatmap colors.

        Args:
            color_min (float|None): Minimum value mapped to the start of the colormap.
            color_max (float|None): Maximum value mapped to the end of the colormap.

        If either bound is ``None`` the corresponding limit is inferred from the data.
        Raises ``ValueError`` if both bounds are provided and ``color_min`` is not
        strictly smaller than ``color_max``.
        """
        if color_min is not None and color_max is not None and color_min >= color_max:
            raise ValueError("color_min must be smaller than color_max")

        self._color_min = float(color_min) if color_min is not None else None
        self._color_max = float(color_max) if color_max is not None else None
        self.on_data_changed()

    @property
    def target_render_time(self):
        return self._target_render_time

    @target_render_time.setter
    def target_render_time(self, ms):
        self._target_render_time = float(ms)
        # Trigger update to adapt immediately
        self.on_data_changed()

    @property
    def neighbors(self):
        return self._neighbors

    @neighbors.setter
    def neighbors(self, value):
        if value < 1:
            raise ValueError("Neighbors must be at least 1")
        self._neighbors = int(value)
        self.on_data_changed()

    @property
    def kernel(self) -> KernelType:
        return self._kernel

    @kernel.setter
    def kernel(self, value: KernelType):
        if value == "":
            value = "thin_plate_spline"

        valid_kernels = [
            "thin_plate_spline",
            "linear",
            "cubic",
            "quintic",
            "gaussian",
            "multiquadric",
            "inverse_multiquadric",
        ]
        if value not in valid_kernels:
            raise ValueError(f"Invalid kernel: {value}")
        self._kernel = value
        self.on_data_changed()

    @property
    def quality(self) -> QualityLevel:
        if self._is_adaptive:
            return "adaptive"
        if self._idle_grid_size <= 50:
            return "very low"
        if self._idle_grid_size <= 100:
            return "low"
        if self._idle_grid_size <= 150:
            return "medium"
        if self._idle_grid_size <= 300:
            return "high"
        return "very high"

    @quality.setter
    def quality(self, value: Union[QualityLevel, str, int]):
        if isinstance(value, str):
            value = value.lower()

        if value == "very low":
            self._is_adaptive = False
            self._preview_grid_size = 30
            self._idle_grid_size = 50
        elif value in ["low", 0]:
            self._is_adaptive = False
            self._preview_grid_size = 50
            self._idle_grid_size = 100
        elif value in ["medium", 1]:
            self._is_adaptive = False
            self._preview_grid_size = 75
            self._idle_grid_size = 150
        elif value in ["high", 2]:
            self._is_adaptive = False
            self._preview_grid_size = 100
            self._idle_grid_size = 300
        elif value == "very high":
            self._is_adaptive = False
            self._preview_grid_size = 150
            self._idle_grid_size = 500
        elif value == "adaptive":
            self._is_adaptive = True
            # Start with Medium
            self._preview_grid_size = 75
            self._idle_grid_size = 150
        else:
            print(f"Warning: Invalid quality '{value}'. Ignoring.")

        self.on_data_changed()

    def set_boundary_shape(self, shape: Union[QPolygonF, QRectF, QPainterPath]):
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
        if not hasattr(self, "_idle_grid_size"):
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

                rect = QRectF(
                    min_x - padding_x,
                    min_y - padding_y,
                    width + 2 * padding_x,
                    height + 2 * padding_y,
                )
                self._boundary_shape = QPolygonF(rect)
                self.set_bounding_rect(rect)
            else:
                self._boundary_shape = QPolygonF()
                self.set_bounding_rect(QRectF())

        # 1. Cancel any pending HQ update
        if hasattr(self, "_hq_timer"):
            self._hq_timer.stop()

        # 2. Perform Fast Update (Low-Res RBF)
        # Use 1/10th of the grid size for speed (e.g., 30x30 instead of 300x300)
        # 2. Perform Fast Update (Preview Quality)
        self._generate_heatmap(
            method="rbf", neighbors=self._neighbors, grid_size=self._preview_grid_size
        )
        self.update()

        # 3. Schedule High Quality Update
        if hasattr(self, "_hq_timer"):
            self._hq_timer.start()

    def _perform_hq_update(self):
        """
        Slot for HQ timer timeout. Performs RBF interpolation.
        """
        self._generate_heatmap(
            method="rbf", neighbors=self._neighbors, grid_size=self._idle_grid_size
        )
        self.update()

    def _generate_heatmap(
        self, method: str = "rbf", neighbors: int = 30, grid_size: Optional[int] = None
    ):
        """
        Generates the heatmap image using cached interpolators.
        """
        start_time = time.perf_counter()

        if grid_size is None:
            grid_size = self._idle_grid_size

        points, values, _ = self.get_valid_data()

        if len(points) < 3 or self._boundary_shape.isEmpty():
            self._cached_image = None
            return

        # Get Interpolator from Cache
        # This handles geometry checks and fitting internally
        rbf_interp, boundary_gen = self._interpolator_cache.get_interpolator(
            grid_size, points, self._boundary_shape, neighbors, kernel=self._kernel
        )

        # We need to reconstruct the expanded grid size for reshaping
        # This logic must match what's inside InterpolatorCache
        # Ideally InterpolatorCache should return this info, but for now we re-calculate
        # or we can store it in the interpolator object if we modify it.
        # Let's re-calculate for safety as it's cheap.
        expanded_grid_size = grid_size + 2
        self._last_grid_shape = (expanded_grid_size, expanded_grid_size)

        # Also need to update self._heatmap_rect for drawing
        rect = self._boundary_shape.boundingRect()
        dx = rect.width() / grid_size
        dy = rect.height() / grid_size
        self._heatmap_rect = rect.adjusted(-dx, -dy, dx, dy)

        # --- Fast Update Phase (Values Only) ---

        # 1. Get Boundary Values
        boundary_values = boundary_gen.transform(values)

        # 2. Combine Values
        if len(boundary_values) > 0:
            all_values = np.concatenate((values, boundary_values))
        else:
            all_values = values

        # 3. Predict
        Z_flat = rbf_interp.predict(all_values)

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
        if (
            self._is_adaptive
            and grid_size == self._idle_grid_size
            and self._target_render_time > 0
            and duration_ms > 0
        ):
            # Calculate ideal grid size based on target time
            # time ~ grid^2  =>  grid ~ sqrt(time)
            ratio = self._target_render_time / duration_ms
            ideal_grid = int(self._idle_grid_size * np.sqrt(ratio))

            # Find closest tier
            # We prefer a tier that is slightly lower or equal to ideal to be safe on performance
            # or just closest. Let's pick closest tier <= ideal_grid to ensure we meet target time.

            # Find closest tier index
            current_tier_idx = 0
            try:
                current_tier_idx = TIERS.index(self._idle_grid_size)
            except ValueError:
                # If current size is not in tiers, find closest
                current_tier_idx = min(
                    range(len(TIERS)),
                    key=lambda i: abs(TIERS[i] - self._idle_grid_size),
                )

            target_tier_idx = 0
            for i, tier in enumerate(TIERS):
                if tier <= ideal_grid:
                    target_tier_idx = i
                else:
                    break

            # Constrain to max 1 step change
            if target_tier_idx > current_tier_idx:
                target_tier_idx = current_tier_idx + 1
            elif target_tier_idx < current_tier_idx:
                target_tier_idx = current_tier_idx - 1

            # Clamp index
            target_tier_idx = max(0, min(len(TIERS) - 1, target_tier_idx))

            new_tier = TIERS[target_tier_idx]

            # Only update if changed
            if new_tier != self._idle_grid_size:
                self._idle_grid_size = new_tier

                # Update preview size (approx 1/3 of idle, min 30)
                self._preview_grid_size = max(30, int(self._idle_grid_size / 3))

                print(
                    f"[Adaptive] Render: {duration_ms:.1f}ms, Target: {self._target_render_time}ms -> New Idle: {self._idle_grid_size}, Preview: {self._preview_grid_size}"
                )

    def _array_to_qimage(self, Z: np.ndarray) -> QImage:
        """
        Converts 2D array Z to QImage using vectorized operations.
        """
        height, width = Z.shape

        # 1. Normalize Z to 0-255 indices
        Z_norm = np.nan_to_num(Z, nan=-1)

        # Mask for transparent pixels
        mask = Z_norm == -1
        valid_values = Z_norm[~mask]

        # Determine normalization bounds
        if valid_values.size > 0:
            min_val = (
                self._color_min
                if self._color_min is not None
                else float(np.nanmin(valid_values))
            )
            max_val = (
                self._color_max
                if self._color_max is not None
                else float(np.nanmax(valid_values))
            )
        else:
            min_val = self._color_min if self._color_min is not None else 0.0
            max_val = self._color_max if self._color_max is not None else 1.0

        if max_val == min_val:
            max_val = min_val + 1e-9

        # Normalize valid values to 0.0-1.0
        normalized = np.clip((Z_norm - min_val) / (max_val - min_val), 0.0, 1.0)

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
        if not buffer.flags["C_CONTIGUOUS"]:
            buffer = np.ascontiguousarray(buffer)

        image = QImage(
            buffer.data, width, height, width * 4, QImage.Format.Format_ARGB32
        )

        # We must copy the image data because QImage doesn't own the buffer
        # and 'buffer' might be garbage collected after this function returns.
        return image.copy()

    def paint(
        self,
        painter: "QPainter",
        option: "QStyleOptionGraphicsItem",
        widget: Optional["QWidget"] = None,
    ) -> None:
        if self._cached_image:
            # Clip to polygon
            path = QPainterPath()
            path.addPolygon(self._boundary_shape)
            painter.setClipPath(path)

            # Draw the expanded heatmap
            # Enable smooth transformation for upscaling low-res images
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            painter.drawImage(self._heatmap_rect, self._cached_image)
