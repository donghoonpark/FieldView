import sys
import os
import numpy as np
from PySide6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene
from PySide6.QtGui import QPolygonF
from PySide6.QtCore import Qt, QPointF

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fieldview.core.data_container import DataContainer
from fieldview.layers.heatmap_layer import HeatmapLayer
from fieldview.layers.text_layer import ValueLayer
from fieldview.layers.svg_layer import SvgLayer
from fieldview.layers.pin_layer import PinLayer

def run():
    # Check if QApplication already exists (for testing/script usage)
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    # 1. Setup Data
    data = DataContainer()
    # Use fixed seed for consistent screenshot
    np.random.seed(41)
    
    # Define rooms (x1, y1, x2, y2)
    rooms = [
        (-450, -250, -150, 250), # Master Bed
        (-150, -250, 150, 250),  # Living
        (150, 0, 300, 250),      # Bed 2
        (300, -100, 450, 250)    # Bed 4
    ]
    
    points = []
    values = []
    
    for i in range(20):
        room = rooms[np.random.randint(len(rooms))]
        x1, y1, x2, y2 = room
        margin = 20
        x = np.random.uniform(x1 + margin, x2 - margin)
        y = np.random.uniform(y1 + margin, y2 - margin)
        points.append([x, y])
        values.append(np.random.rand() * 100)
        
    data.set_data(np.array(points), np.array(values))

    # 2. Create Scene & Layers
    scene = QGraphicsScene()
    
    # SVG Layer (Background)
    svg_path = os.path.join(os.path.dirname(__file__), 'floorplan_apartment.svg')
    svg_layer = SvgLayer()
    svg_layer.load_svg(svg_path)
    svg_layer.setZValue(0)
    scene.addItem(svg_layer)
    
    # Heatmap Layer (Data Visualization)
    heatmap = HeatmapLayer(data)
    heatmap.setOpacity(0.6)
    heatmap.setZValue(1)
    
    # Define custom boundary polygon for the apartment
    polygon = QPolygonF([
        QPointF(-450, -330), QPointF(-300, -330), QPointF(-300, -250),
        QPointF(-150, -250), QPointF(-150, -300), QPointF(150, -300), 
        QPointF(150, -250), QPointF(450, -250), QPointF(450, 250), 
        QPointF(-450, 250)
    ])
    heatmap.set_boundary_shape(polygon)
    
    scene.addItem(heatmap)
    
    # Pin Layer (Markers)
    pin_layer = PinLayer(data)
    pin_layer.setZValue(2)
    scene.addItem(pin_layer)
    
    # Value Layer (Labels)
    values_layer = ValueLayer(data)
    values_layer.update_layer()
    values_layer.setZValue(3)
    scene.addItem(values_layer)

    # 3. Setup View
    view = QGraphicsView()
    view.setScene(scene)
    view.resize(600, 600)
    
    # Ensure the content is visible
    view.show()
    # Fit in view after showing
    scene.setSceneRect(scene.itemsBoundingRect())
    view.fitInView(scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    return app, view

if __name__ == "__main__":
    app, view = run()
    sys.exit(app.exec())
