import sys
import numpy as np
from qtpy.QtWidgets import QApplication
from fieldview.ui.field_view import FieldView


def main():
    app = QApplication(sys.argv)

    view = FieldView()
    view.resize(800, 600)
    view.setWindowTitle("FieldView Interactive Demo")

    # Add some dummy data
    points = np.random.rand(10, 2) * 400 - 200
    values = np.random.rand(10)
    view.set_data(points, values)

    # Add layers
    view.add_heatmap_layer()
    view.add_pin_layer()
    view.add_value_layer()

    view.show()
    view.fit_to_scene()

    print("Use mouse wheel to zoom, click and drag to pan.")

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
