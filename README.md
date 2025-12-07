# FieldView

[![Quality](https://github.com/donghoonpark/FieldView/actions/workflows/quality.yml/badge.svg)](https://github.com/donghoonpark/FieldView/actions/workflows/quality.yml)
[![Tests](https://github.com/donghoonpark/FieldView/actions/workflows/tests.yml/badge.svg)](https://github.com/donghoonpark/FieldView/actions/workflows/tests.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)

**FieldView** is a high-performance Python library for 2D data visualization, built on top of the Qt framework. It is designed to efficiently render irregular data points using heatmaps, markers, and text labels.

FieldView leverages `QtPy` to support **PySide6**, **PyQt6**, and **PyQt5**, providing a flexible and robust solution for integrating advanced visualizations into Python desktop applications.

<img src="assets/us_map_demo.png" alt="FieldView Demo" width="800">

## Key Features

*   **High-Performance Heatmaps**: Utilizes hybrid RBF (Radial Basis Function) interpolation for smooth, high-quality visualization of scattered data.
*   **Irregular Data Handling**: Natively supports non-grid data points without requiring pre-processing.
*   **Flexible Masking**: Supports arbitrary boundary shapes (Polygon, Circle, Rectangle) for precise clipping.
*   **Modular Layer System**:
    *   **HeatmapLayer**: Renders interpolated data with customizable colormaps.
    *   **ValueLayer / LabelLayer**: Displays text with automatic collision avoidance.
    *   **PinLayer**: Visualizes data points with markers.
    *   **SvgLayer**: Renders SVG backgrounds for context (e.g., floor plans, maps).
*   **Minimal Dependencies**: Core functionality relies only on `numpy`, `scipy`, and `qtpy`.

## Performance

FieldView's `FastRBFInterpolator` is designed for real-time rendering. By precomputing the interpolation matrix, it achieves significant speedups during the rendering phase.

![Benchmark Plot](benchmark_plot.png)

*Note: FastRBF requires a one-time setup cost to accelerate subsequent frame rendering.*

## Installation

Install FieldView with your preferred Qt binding:

```bash
pip install fieldview[pyside6]  # Recommended
# OR
pip install fieldview[pyqt6]
# OR
pip install fieldview[pyqt5]
```

*Requires Python 3.10+*

## Quick Start

FieldView provides a high-level `FieldView` widget for easy integration.

```python
import sys
import numpy as np
from qtpy.QtWidgets import QApplication
from fieldview import FieldView

app = QApplication(sys.argv)

# 1. Prepare Data
points = np.random.rand(20, 2) * 400
values = np.random.rand(20) * 100

# 2. Create FieldView
view = FieldView()
view.resize(800, 600)
view.set_data(points, values)

# 3. Add Layers
view.add_heatmap_layer(opacity=0.6)
view.add_pin_layer()
view.add_value_layer()

# 4. Show
view.show()
view.fit_to_scene()

sys.exit(app.exec())
```

## Examples

To explore the full capabilities, including the property inspector and real-time updates, run the included demo:

```bash
# Using uv (recommended)
uv run examples/demo.py
```

## License

This project is licensed under a hybrid model depending on the Qt binding used:

*   **LGPLv3**: When used with **PySide6**.
*   **GPLv3**: When used with **PyQt6** or **PyQt5**.

Please ensure compliance with the license of the chosen Qt binding.
