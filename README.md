# FieldView

**FieldView** is a high-performance Python + Qt (PySide6) library for 2D data visualization, specifically designed for handling irregular data points. It provides a robust rendering engine for heatmaps, markers, and text labels with minimal external dependencies.

## Key Features

*   **Fast Heatmap Rendering**: Hybrid RBF (Radial Basis Function) interpolation for high-quality visualization with real-time performance optimization.
*   **Irregular Data Support**: Native handling of non-grid data points.
*   **Polygon Masking**: Support for arbitrary boundary shapes (Polygon, Circle, Rectangle) to clip heatmaps.
*   **Layer System**: Modular architecture with support for:
    *   **HeatmapLayer**: Color-based data visualization.
    *   **ValueLayer/LabelLayer**: Text rendering with collision avoidance.
    *   **PinLayer**: Marker placement.
    *   **SvgLayer**: Background floor plans or overlays.
*   **Minimal Dependencies**: Built on `numpy`, `scipy`, and `PySide6`.

## Installation

```bash
pip install fieldview
```

*Note: Requires Python 3.10+*

## Quick Start

Here is a minimal example to get a heatmap up and running:

```python
import sys
import numpy as np
from PySide6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene
from fieldview.core.data_container import DataContainer
from fieldview.layers.heatmap_layer import HeatmapLayer

app = QApplication(sys.argv)

# 1. Setup Data
data = DataContainer()
points = np.random.rand(20, 2) * 300  # 20 random points
values = np.random.rand(20) * 100     # Random values
data.set_data(points, values)

# 2. Create Scene & Layer
scene = QGraphicsScene()
heatmap = HeatmapLayer(data)
scene.addItem(heatmap)

# 3. Setup View
view = QGraphicsView(scene)
view.resize(800, 600)
view.show()

sys.exit(app.exec())
```

## Running the Demo

To see all features in action, including the property editor and real-time interaction:

```bash
# Clone the repository
git clone https://github.com/yourusername/fieldview.git
cd fieldview

# Install dependencies
pip install -e .[dev]

# Run the demo
python examples/demo.py
```

## License

MIT License
