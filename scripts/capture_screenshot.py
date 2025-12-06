import sys
import os
import numpy as np

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

# Set offscreen platform before importing qtpy
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_API"] = "pyside6"

# Add project root to path BEFORE importing fieldview or qtpy
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene
    from PySide6.QtGui import QImage, QPainter, QColor
    from PySide6.QtCore import QTimer, Qt
else:
    from qtpy.QtWidgets import QApplication, QGraphicsView, QGraphicsScene
    from qtpy.QtGui import QImage, QPainter, QColor
    from qtpy.QtCore import QTimer, Qt

from fieldview.core.data_container import DataContainer
from fieldview.layers.heatmap_layer import HeatmapLayer
from fieldview.layers.text_layer import ValueLayer
from fieldview.layers.svg_layer import SvgLayer

from examples.us_map_utils import (
    get_state_data,
    get_us_boundary,
    load_weather_data,
    generate_us_dataset,
)


def capture():
    app = QApplication(sys.argv)

    svg_file = os.path.join(os.path.dirname(__file__), "..", "examples", "us_map.svg")
    if not os.path.exists(svg_file):
        print(f"Error: {svg_file} not found")
        return

    # 1. Parse SVG for Geometry
    state_paths, centroids = get_state_data(svg_file)

    # Create combined boundary path for heatmap
    us_boundary = get_us_boundary(state_paths)

    # 2. Setup Data
    dc = DataContainer()

    # Load Weather Data
    weather_data = load_weather_data()

    # Generate Dataset
    points, values = generate_us_dataset(centroids, weather_data)

    dc.set_data(points, values)

    # 3. Setup Scene
    scene = QGraphicsScene(0, 0, 959, 593)
    scene.setBackgroundBrush(
        Qt.GlobalColor.white
    )  # Solid white background by user request

    # 4. Layers
    # SVG Map
    svg_layer = SvgLayer()
    svg_layer.load_svg(svg_file)

    scene.addItem(svg_layer)

    # Heatmap
    heatmap = HeatmapLayer(dc)
    heatmap.setOpacity(0.8)  # Lowered from 0.6 by user request
    heatmap.colormap = "jet"  # Changed from default (viridis) to jet by user request
    heatmap.neighbors = 100  # Global interpolation for smooth gradients
    heatmap.kernel = "thin_plate_spline"
    heatmap.quality = "low"
    # Set the exact US boundary
    heatmap.set_boundary_shape(us_boundary)
    scene.addItem(heatmap)

    # Values
    values_layer = ValueLayer(dc)
    values_layer.suffix = "°C"
    values_layer.font.setPixelSize(14)
    values_layer.font.setBold(True)
    values_layer.highlight_color = QColor("orange")

    # Highlight highest temp
    max_idx = np.argmax(values)
    values_layer.set_highlighted_indices([int(max_idx)])
    scene.addItem(values_layer)

    # 5. View
    view = QGraphicsView(scene)
    view.resize(959, 593)

    # Set scene rect to match SVG (959x593)
    scene.setSceneRect(0, 0, 959, 593)

    # 6. Capture
    assets_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
    os.makedirs(assets_dir, exist_ok=True)
    output_path = os.path.join(assets_dir, "us_map_demo.png")

    def take_screenshot():
        print("Rendering...")
        image = QImage(959, 593, QImage.Format.Format_ARGB32)
        image.fill(QColor(30, 30, 30))

        painter = QPainter(image)
        scene.render(painter)
        painter.end()

        image.save(output_path)
        print(f"Saved to {output_path}")
        app.quit()

    QTimer.singleShot(2000, take_screenshot)
    sys.exit(app.exec())


if __name__ == "__main__":
    capture()
