import sys
import os
import numpy as np
import pandas as pd
from PySide6.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene, 
                               QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                               QSlider, QFileDialog, QDockWidget, QGroupBox, QComboBox)
from PySide6.QtGui import QPainter, QPolygonF, QColor
from PySide6.QtCore import Qt, QTimer, QPointF

# Add project root to sys.path to import fieldview modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fieldview.core.data_container import DataContainer
from fieldview.layers.heatmap_layer import HeatmapLayer
from examples.generate_data import generate_dummy_data

class HeatmapDemo(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FieldView Heatmap Demo")
        self.resize(1000, 800)
        
        # Core Components
        self.data_container = DataContainer()
        self.scene = QGraphicsScene()
        self.heatmap_layer = HeatmapLayer(self.data_container)
        
        # Setup Scene
        self.scene.addItem(self.heatmap_layer)
        self.scene.setBackgroundBrush(Qt.GlobalColor.black)
        
        # View
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setCentralWidget(self.view)
        
        # Controls (Dock)
        self.setup_controls()
        
        # Initial Data
        self.generate_random_data()
        
        # Status Bar
        self.status_label = QLabel("Ready")
        self.statusBar().addWidget(self.status_label)
        self.data_container.dataChanged.connect(self.update_status)

    def setup_controls(self):
        dock = QDockWidget("Controls", self)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Data Actions
        group_data = QGroupBox("Data Actions")
        layout_data = QVBoxLayout(group_data)
        
        btn_load = QPushButton("Load CSV")
        btn_load.clicked.connect(self.load_csv)
        layout_data.addWidget(btn_load)
        
        btn_gen = QPushButton("Generate Random")
        btn_gen.clicked.connect(self.generate_random_data)
        layout_data.addWidget(btn_gen)
        
        btn_add = QPushButton("Add Random Point")
        btn_add.clicked.connect(self.add_random_point)
        layout_data.addWidget(btn_add)
        
        btn_remove = QPushButton("Remove Random Point")
        btn_remove.clicked.connect(self.remove_random_point)
        layout_data.addWidget(btn_remove)
        
        btn_clear = QPushButton("Clear Data")
        btn_clear.clicked.connect(self.data_container.clear)
        layout_data.addWidget(btn_clear)
        
        layout.addWidget(group_data)
        
        # Layer Actions
        group_layer = QGroupBox("Layer Actions")
        layout_layer = QVBoxLayout(group_layer)
        
        lbl_shape = QLabel("Boundary Shape:")
        layout_layer.addWidget(lbl_shape)
        
        combo_shape = QComboBox()
        combo_shape.addItems(["Square", "Circle", "Triangle", "Hexagon"])
        combo_shape.currentTextChanged.connect(self.update_shape)
        layout_layer.addWidget(combo_shape)
        
        btn_exclude = QPushButton("Toggle Exclusion (Random)")
        btn_exclude.clicked.connect(self.toggle_exclusion)
        layout_layer.addWidget(btn_exclude)
        
        layout.addWidget(group_layer)
        
        layout.addStretch()
        dock.setWidget(widget)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

    def load_csv(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open CSV", "", "CSV Files (*.csv)")
        if filename:
            try:
                df = pd.read_csv(filename)
                if 'x' in df.columns and 'y' in df.columns and 'value' in df.columns:
                    points = df[['x', 'y']].values
                    values = df['value'].values
                    self.data_container.set_data(points, values)
                    self.status_label.setText(f"Loaded {len(points)} points from {os.path.basename(filename)}")
                else:
                    self.status_label.setText("Error: CSV must have x, y, value columns")
            except Exception as e:
                self.status_label.setText(f"Error loading CSV: {e}")

    def generate_random_data(self):
        df = generate_dummy_data(n_points=50)
        points = df[['x', 'y']].values
        values = df['value'].values
        self.data_container.set_data(points, values)

    def add_random_point(self):
        # Generate random point in square range [-150, 150]
        radius = 150
        x = (np.random.rand() - 0.5) * 2 * radius
        y = (np.random.rand() - 0.5) * 2 * radius
        value = np.random.rand() * 100
        
        self.data_container.add_points([[x, y]], [value])

    def remove_random_point(self):
        count = len(self.data_container.points)
        if count > 0:
            idx = np.random.randint(0, count)
            self.data_container.remove_points([idx])

    def update_shape(self, shape_name):
        radius = 150
        polygon = QPolygonF()
        
        if shape_name == "Square":
            polygon.append(QPointF(-radius, -radius))
            polygon.append(QPointF(radius, -radius))
            polygon.append(QPointF(radius, radius))
            polygon.append(QPointF(-radius, radius))
        elif shape_name == "Circle":
            n_points = 60
            for i in range(n_points):
                theta = 2 * np.pi * i / n_points
                polygon.append(QPointF(radius * np.cos(theta), radius * np.sin(theta)))
        elif shape_name == "Triangle":
            for i in range(3):
                theta = 2 * np.pi * i / 3 - np.pi / 2
                polygon.append(QPointF(radius * np.cos(theta), radius * np.sin(theta)))
        elif shape_name == "Hexagon":
            for i in range(6):
                theta = 2 * np.pi * i / 6
                polygon.append(QPointF(radius * np.cos(theta), radius * np.sin(theta)))
                
        self.heatmap_layer.set_boundary_shape(polygon)
        self.status_label.setText(f"Shape set to {shape_name}")

    def toggle_exclusion(self):
        count = len(self.data_container.points)
        if count == 0: return
        
        idx = np.random.randint(0, count)
        if idx in self.heatmap_layer.excluded_indices:
            self.heatmap_layer.remove_excluded_index(idx)
            self.status_label.setText(f"Included point {idx}")
        else:
            self.heatmap_layer.add_excluded_index(idx)
            self.status_label.setText(f"Excluded point {idx}")

    def update_status(self):
        count = len(self.data_container.points)
        self.status_label.setText(f"Data Points: {count}")

if __name__ == "__main__":
    from PySide6.QtGui import QPainter # Import here to avoid circular dependency issues if any
    app = QApplication(sys.argv)
    window = HeatmapDemo()
    window.show()
    sys.exit(app.exec())
