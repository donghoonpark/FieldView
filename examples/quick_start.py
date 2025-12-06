import sys
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication
else:
    from qtpy.QtWidgets import QApplication

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fieldview import FieldView
from examples.us_map_utils import (
    get_state_data,
    get_us_boundary,
    load_weather_data,
    generate_us_dataset,
)


def run():
    # Check if QApplication already exists (for testing/script usage)
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    # 1. Setup Data
    # Load US Map Data
    svg_file = os.path.join(os.path.dirname(__file__), "us_map.svg")
    state_paths, centroids = get_state_data(svg_file)

    # Load Weather Data
    weather_data = load_weather_data()

    # Generate Dataset
    points, values = generate_us_dataset(centroids, weather_data)

    # 2. Create FieldView
    view = FieldView()
    view.resize(1200, 800)
    view.set_data(points, values)

    # 3. Add Layers

    # SVG Layer (Background)
    view.add_svg_layer(svg_file)

    # Heatmap Layer (Data Visualization)
    heatmap = view.add_heatmap_layer(opacity=0.6)

    # Setup Heatmap Boundary
    us_boundary = get_us_boundary(state_paths)
    heatmap.set_boundary_shape(us_boundary)
    heatmap.neighbors = 100  # Adjust for US map scale

    # Pin Layer (Markers)
    view.add_pin_layer()

    # Value Layer (Labels)
    view.add_value_layer()

    # 4. Show View
    view.show()
    view.fit_to_scene()

    return app, view


if __name__ == "__main__":
    app, view = run()
    sys.exit(app.exec())
