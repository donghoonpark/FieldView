import sys
import time
import numpy as np
from scipy.interpolate import RBFInterpolator, LinearNDInterpolator
from scipy.spatial import cKDTree
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import (
        QApplication,
        QMainWindow,
        QGraphicsView,
        QGraphicsScene,
        QWidget,
        QVBoxLayout,
        QPushButton,
        QLabel,
    )
    from PySide6.QtGui import QPainter, QColor, QPolygonF, QImage
    from PySide6.QtCore import Qt, QTimer, QPoint
else:
    from qtpy.QtWidgets import (
        QApplication,
        QMainWindow,
        QGraphicsView,
        QGraphicsScene,
        QWidget,
        QVBoxLayout,
        QPushButton,
        QLabel,
    )
    from qtpy.QtGui import QPainter, QColor, QPolygonF, QImage
    from qtpy.QtCore import Qt, QTimer, QPoint


def generate_data(n_points=25, radius=150):
    """Generates random data points within a circle."""
    # Random radius and angle
    r = radius * np.sqrt(np.random.rand(n_points))
    theta = np.random.rand(n_points) * 2 * np.pi

    x = r * np.cos(theta)
    y = r * np.sin(theta)

    # Generate values with a gradient (Left -> Right)
    # Normalize x from [-radius, radius] to [0, 1] roughly
    normalized_x = (x + radius) / (2 * radius)

    # Base gradient value (0 to 80)
    base_values = normalized_x * 80

    # Add some random noise (-10 to 10)
    noise = (np.random.rand(n_points) - 0.5) * 20

    values = base_values + noise

    # Clip values to 0-100 range
    values = np.clip(values, 0, 100)

    return np.column_stack((x, y)), values


def get_boundary_points(data_points, radius=150):
    """Generates ghost points on the boundary using adaptive sampling."""
    # 1. Calculate Average Nearest Neighbor Distance (ANND)
    tree = cKDTree(data_points)
    distances, _ = tree.query(
        data_points, k=2
    )  # k=2 because the first neighbor is the point itself
    avg_dist = np.mean(distances[:, 1])

    # 2. Determine target segment length (1.0 ~ 1.5x ANND)
    target_segment_length = avg_dist * 1.2

    # 3. Calculate circumference and number of points needed
    circumference = 2 * np.pi * radius
    n_boundary_points = int(np.ceil(circumference / target_segment_length))

    # 4. Generate points
    theta = np.linspace(0, 2 * np.pi, n_boundary_points, endpoint=False)
    x = radius * np.cos(theta)
    y = radius * np.sin(theta)

    return np.column_stack((x, y))


def interpolate(
    data_points,
    data_values,
    boundary_points,
    radius=150,
    grid_size=300,
    method="rbf",
    neighbors=30,
):
    """Performs interpolation using data points + ghost points."""
    start_time = time.perf_counter()

    # Calculate values for boundary points using IDW of 2 nearest data points
    tree = cKDTree(data_points)
    # Query 2 nearest neighbors
    dists, indices = tree.query(boundary_points, k=2)

    boundary_values = []
    for i in range(len(boundary_points)):
        d1, d2 = dists[i]
        idx1, idx2 = indices[i]
        v1, v2 = data_values[idx1], data_values[idx2]

        # Avoid division by zero
        if d1 < 1e-9:
            val = v1
        elif d2 < 1e-9:
            val = v2
        else:
            w1 = 1.0 / d1
            w2 = 1.0 / d2
            val = (w1 * v1 + w2 * v2) / (w1 + w2)
        boundary_values.append(val)

    boundary_values_arr = np.array(boundary_values)

    # Combine data and ghost points
    all_points = np.vstack((data_points, boundary_points))
    all_values = np.concatenate((data_values, boundary_values_arr))

    # Create grid
    x = np.linspace(-radius, radius, grid_size)
    y = np.linspace(-radius, radius, grid_size)
    X, Y = np.meshgrid(x, y)

    try:
        if method == "linear":
            # Linear Interpolation (Fast)
            interp = LinearNDInterpolator(all_points, all_values, fill_value=np.nan)
            Z = interp(X, Y)
        else:  # method == 'rbf'
            # RBF Interpolation (High Quality)
            # Flatten grid for RBFInterpolator
            grid_points = np.column_stack((X.ravel(), Y.ravel()))
            interp = RBFInterpolator(
                all_points, all_values, neighbors=neighbors, kernel="thin_plate_spline"
            )
            Z_flat = interp(grid_points)
            Z = Z_flat.reshape(grid_size, grid_size)

    except Exception as e:
        print(f"Interpolation failed: {e}")
        return np.zeros((grid_size, grid_size)), 0.0

    # Mask out points outside the circle
    mask = (X**2 + Y**2) > radius**2
    Z[mask] = np.nan

    end_time = time.perf_counter()
    elapsed_ms = (end_time - start_time) * 1000
    return Z, elapsed_ms


class HeatmapWidget(QWidget):
    def __init__(self, radius=150):
        super().__init__()
        self.radius = radius
        self.setFixedSize(radius * 2 + 20, radius * 2 + 60)  # Extra space for button

        self.Z = None
        self.data_points = []
        self.boundary_points = []
        self.data_values = []

        # Timer for High Quality update
        self.hq_timer = QTimer(self)
        self.hq_timer.setSingleShot(True)
        self.hq_timer.setInterval(300)  # 300ms
        self.hq_timer.timeout.connect(self.perform_hq_update)

        # Layout
        layout = QVBoxLayout(self)
        layout.addStretch()

        self.btn_regen = QPushButton("Regenerate Data (Click me!)")
        self.btn_regen.clicked.connect(self.regenerate_data)
        layout.addWidget(self.btn_regen)

        self.lbl_status = QLabel("Ready")
        self.lbl_status.setStyleSheet("color: white;")
        layout.addWidget(self.lbl_status)

        # Initial data
        self.regenerate_data()

    def regenerate_data(self):
        # 1. Generate new data
        n_points = 25
        self.data_points, self.data_values = generate_data(n_points, self.radius)
        self.boundary_points = get_boundary_points(self.data_points, self.radius)

        # 2. Perform Fast Update (Linear)
        self.perform_update(
            method="linear", neighbors=None, quality_label="Fast (Linear)"
        )

        # 3. Schedule High Quality Update
        self.hq_timer.start()

    def perform_hq_update(self):
        # Perform High Quality Update (RBF, neighbors=30)
        self.perform_update(
            method="rbf", neighbors=25, quality_label="High Quality (RBF k=30)"
        )

    def perform_update(self, method, neighbors, quality_label):
        self.lbl_status.setText(f"Rendering: {quality_label}...")
        QApplication.processEvents()  # Force UI update

        self.Z, elapsed_ms = interpolate(
            self.data_points,
            self.data_values,
            self.boundary_points,
            self.radius,
            method=method,
            neighbors=neighbors,
        )

        status_text = f"Mode: {quality_label} | Time: {elapsed_ms:.2f} ms"
        print(status_text)
        self.lbl_status.setText(status_text)
        self.update()  # Trigger paintEvent

    def paintEvent(self, event):
        if self.Z is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Convert Z to QImage
        height, width = self.Z.shape
        image = QImage(width, height, QImage.Format.Format_ARGB32)

        # Simple colormap (Blue -> Red)
        # Normalize Z to 0-255
        Z_norm = np.nan_to_num(self.Z, nan=-1)
        max_val = np.nanmax(Z_norm)
        if max_val == 0:
            max_val = 1

        for y in range(height):
            for x in range(width):
                val = Z_norm[y, x]
                if val == -1:  # Masked
                    color = QColor(0, 0, 0, 0)  # Transparent
                else:
                    ratio = val / max_val
                    # Clamp ratio to 0.0 - 1.0
                    ratio = max(0.0, min(1.0, ratio))

                    # Simple heatmap: Blue(0) -> Red(1)
                    r = int(255 * ratio)
                    b = int(255 * (1 - ratio))
                    color = QColor(r, 0, b, 255)

                image.setPixelColor(x, y, color)

        # Draw image centered
        painter.drawImage(10, 10, image)

        # Draw circle border
        painter.setPen(Qt.GlobalColor.white)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(10, 10, self.radius * 2, self.radius * 2)

        # Helper to transform coordinates
        def to_screen(x, y):
            sx = x + self.radius + 10
            sy = y + self.radius + 10
            return QPoint(int(sx), int(sy))

        # Draw boundary points (Ghost points) - Red small dots
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 0, 0, 150))
        for px, py in self.boundary_points:
            pt = to_screen(px, py)
            painter.drawEllipse(pt, 2, 2)

        # Draw data points - Cyan dots with border
        painter.setPen(QColor(0, 0, 0))
        painter.setBrush(QColor(0, 255, 255))
        for px, py in self.data_points:
            pt = to_screen(px, py)
            painter.drawEllipse(pt, 4, 4)


def main():
    app = QApplication(sys.argv)

    widget = HeatmapWidget(radius=150)
    widget.setWindowTitle("FieldView Heatmap POC (Dynamic Quality)")
    widget.setStyleSheet("background-color: #222; color: white;")
    widget.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
