import sys
import os
import numpy as np
import pandas as pd
from PySide6.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene, 
                               QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                               QCheckBox, QGroupBox, QSlider, QComboBox, QTableView, 
                               QHeaderView, QAbstractItemView, QGraphicsEllipseItem, QDockWidget, QGraphicsLineItem)
from PySide6.QtGui import QPainterPath,QPainter, QPolygonF, QColor, QPixmap, QBrush, QPen, QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt, QPointF, QAbstractTableModel, QModelIndex, Signal, QRectF

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fieldview.core.data_container import DataContainer
from fieldview.layers.heatmap_layer import HeatmapLayer
from fieldview.layers.text_layer import ValueLayer, LabelLayer
from fieldview.layers.svg_layer import SvgLayer
from fieldview.layers.pin_layer import PinLayer
from fieldview.rendering.colormaps import COLORMAPS
from examples.generate_data import generate_dummy_data

class PointTableModel(QAbstractTableModel):
    def __init__(self, data_container):
        super().__init__()
        self._data_container = data_container
        self._data_container.dataChanged.connect(self.layoutChanged.emit)
        self._highlighted_indices = set()

    def rowCount(self, parent=QModelIndex()):
        return len(self._data_container.points)

    def columnCount(self, parent=QModelIndex()):
        return 5 # Highlight, X, Y, Value, Label

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
            
        row = index.row()
        col = index.column()
        
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            if col == 1: return f"{self._data_container.points[row][0]:.2f}"
            if col == 2: return f"{self._data_container.points[row][1]:.2f}"
            if col == 3: return f"{self._data_container.values[row]:.2f}"
            if col == 4: return self._data_container.labels[row]
            
        if role == Qt.ItemDataRole.CheckStateRole and col == 0:
            return Qt.CheckState.Checked if row in self._highlighted_indices else Qt.CheckState.Unchecked
            
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid():
            return False
            
        row = index.row()
        col = index.column()
        
        if role == Qt.ItemDataRole.CheckStateRole and col == 0:
            if value == Qt.CheckState.Checked.value:
                self._highlighted_indices.add(row)
            else:
                self._highlighted_indices.discard(row)
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.CheckStateRole])
            return True
            
        if role == Qt.ItemDataRole.EditRole:
            try:
                if col == 1:
                    new_x = float(value)
                    y = self._data_container.points[row][1]
                    self._data_container.update_point(row, point=[new_x, y])
                elif col == 2:
                    new_y = float(value)
                    x = self._data_container.points[row][0]
                    self._data_container.update_point(row, point=[x, new_y])
                elif col == 3:
                    new_val = float(value)
                    self._data_container.update_point(row, value=new_val)
                elif col == 4:
                    self._data_container.update_point(row, label=str(value))
                return True
            except ValueError:
                return False
                
        return False

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return ["Highlight", "X", "Y", "Value", "Label"][section]
        return None

    def flags(self, index):
        flags = super().flags(index)
        if index.column() == 0:
            flags |= Qt.ItemFlag.ItemIsUserCheckable
        else:
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    def get_highlighted_indices(self):
        return list(self._highlighted_indices)

class PolygonHandle(QGraphicsEllipseItem):
    def __init__(self, index, x, y, move_callback, remove_callback):
        super().__init__(-5, -5, 10, 10)
        self.setPos(x, y)
        self.setBrush(QBrush(Qt.GlobalColor.yellow))
        self.setPen(QPen(Qt.GlobalColor.black))
        self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.index = index
        self.move_callback = move_callback
        self.remove_callback = remove_callback

    def itemChange(self, change, value):
        if change == QGraphicsEllipseItem.GraphicsItemChange.ItemPositionChange:
            self.move_callback(self.index, value)
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.remove_callback(self.index)
            event.accept()
        else:
            super().mousePressEvent(event)

class PolygonEdge(QGraphicsLineItem):
    def __init__(self, index, p1, p2, add_callback):
        super().__init__(p1.x(), p1.y(), p2.x(), p2.y())
        self.index = index
        self.add_callback = add_callback
        pen = QPen(Qt.GlobalColor.cyan)
        pen.setWidth(2)
        pen.setStyle(Qt.PenStyle.DashLine)
        self.setPen(pen)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.add_callback(self.index, event.scenePos())
            event.accept()
        else:
            super().mousePressEvent(event)

class AllLayersDemo(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FieldView Comprehensive Demo")
        self.resize(1400, 900)
        
        # 1. Setup Core
        self.data_container = DataContainer()
        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QColor(30, 30, 30))
        
        # 2. Setup Layers
        self.svg_layer = SvgLayer()
        self.create_dummy_svg()
        self.scene.addItem(self.svg_layer)
        
        self.heatmap_layer = HeatmapLayer(self.data_container)
        self.heatmap_layer.setOpacity(0.6)
        self.scene.addItem(self.heatmap_layer)
        
        self.pin_layer = PinLayer(self.data_container)
        # Default dot is used if icon is not set
        self.scene.addItem(self.pin_layer)
        
        self.value_layer = ValueLayer(self.data_container)
        self.value_layer.decimal_places = 1
        self.value_layer.suffix = "°C"
        self.scene.addItem(self.value_layer)
        
        self.label_layer = LabelLayer(self.data_container)
        self.label_layer.setVisible(False)
        self.scene.addItem(self.label_layer)
        
        # 3. Setup View
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setCentralWidget(self.view)
        
        # 4. Setup Controls
        self.setup_controls()
        
        # 5. Initial Data
        self.generate_data()
        
        # Polygon Handles and Edges
        self.polygon_handles = []
        self.polygon_edges = []
        self.heatmap_polygon = QPolygonF([
            QPointF(-200, -200), QPointF(200, -200),
            QPointF(200, 200), QPointF(-200, 200)
        ])
        self.update_heatmap_polygon()

    def wheelEvent(self, event):
        # Zoom
        factor = 1.1
        if event.angleDelta().y() < 0:
            factor = 1.0 / factor
        self.view.scale(factor, factor)

    def create_dummy_svg(self):
        svg_content = b'''
        <svg width="400" height="400" viewBox="-200 -200 400 400" xmlns="http://www.w3.org/2000/svg">
            <rect x="-200" y="-200" width="400" height="400" fill="#222" stroke="#444" stroke-width="2"/>
            <circle cx="0" cy="0" r="150" fill="none" stroke="#555" stroke-width="2" stroke-dasharray="10,10"/>
            <line x1="-200" y1="0" x2="200" y2="0" stroke="#555" stroke-width="1"/>
            <line x1="0" y1="-200" x2="0" y2="200" stroke="#555" stroke-width="1"/>
            <text x="-180" y="-180" fill="#888" font-family="sans-serif" font-size="20">Floor Plan</text>
        </svg>
        '''
        filename = "dummy_map.svg"
        with open(filename, "wb") as f:
            f.write(svg_content)
        self.svg_layer.load_svg(filename)
        
    def create_dummy_pin(self):
        # Create a simple pin icon
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw a pin shape
        painter.setBrush(QBrush(QColor(255, 100, 100)))
        painter.setPen(QPen(Qt.GlobalColor.white, 2))
        painter.drawEllipse(4, 4, 24, 24)
        painter.setBrush(QBrush(Qt.GlobalColor.white))
        painter.drawEllipse(12, 12, 8, 8)
        painter.end()
        
        self.pin_layer.set_icon(pixmap)

    def setup_controls(self):
        dock = QDockWidget("Controls", self)
        dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Layer Visibility
        group_vis = QGroupBox("Layer Visibility")
        layout_vis = QHBoxLayout(group_vis)
        
        check_svg = QCheckBox("SVG")
        check_svg.setChecked(True)
        check_svg.toggled.connect(self.svg_layer.setVisible)
        layout_vis.addWidget(check_svg)
        
        check_heat = QCheckBox("Heatmap")
        check_heat.setChecked(True)
        check_heat.toggled.connect(self.heatmap_layer.setVisible)
        layout_vis.addWidget(check_heat)
        
        check_pin = QCheckBox("Pins")
        check_pin.setChecked(True)
        check_pin.toggled.connect(self.pin_layer.setVisible)
        layout_vis.addWidget(check_pin)
        
        check_val = QCheckBox("Values")
        check_val.setChecked(True)
        check_val.toggled.connect(self.value_layer.setVisible)
        layout_vis.addWidget(check_val)
        
        check_lbl = QCheckBox("Labels")
        check_lbl.setChecked(False)
        check_lbl.toggled.connect(self.label_layer.setVisible)
        layout_vis.addWidget(check_lbl)
        
        check_avoid = QCheckBox("Avoid Collisions")
        check_avoid.setChecked(False)
        def toggle_avoid(checked):
            self.value_layer.collision_avoidance_enabled = checked
            self.label_layer.collision_avoidance_enabled = checked
        check_avoid.toggled.connect(toggle_avoid)
        layout_vis.addWidget(check_avoid)
        
        layout.addWidget(group_vis)
        
        # Text Settings
        group_text = QGroupBox("Text Settings")
        layout_text = QVBoxLayout(group_text)
        
        layout_text.addWidget(QLabel("Collision Offset:"))
        slider_offset = QSlider(Qt.Orientation.Horizontal)
        slider_offset.setRange(50, 150) # 0.5 to 1.5
        slider_offset.setValue(60)
        def update_offset(val):
            factor = val / 100.0
            self.value_layer.collision_offset_factor = factor
            self.label_layer.collision_offset_factor = factor
        slider_offset.valueChanged.connect(update_offset)
        layout_text.addWidget(slider_offset)
        
        layout.addWidget(group_text)
        
        # Heatmap Settings
        group_heat = QGroupBox("Heatmap Settings")
        layout_heat = QVBoxLayout(group_heat)
        
        layout_heat.addWidget(QLabel("Colormap:"))
        combo_cmap = QComboBox()
        combo_cmap.addItems(list(COLORMAPS.keys()))
        combo_cmap.currentTextChanged.connect(lambda n: setattr(self.heatmap_layer, 'colormap', n))
        layout_heat.addWidget(combo_cmap)
        
        layout_heat.addWidget(QLabel("Opacity:"))
        slider_opacity = QSlider(Qt.Orientation.Horizontal)
        slider_opacity.setRange(0, 100)
        slider_opacity.setValue(60)
        slider_opacity.valueChanged.connect(lambda v: self.heatmap_layer.setOpacity(v / 100.0))
        layout_heat.addWidget(slider_opacity)
        
        check_poly = QCheckBox("Edit Polygon")
        check_poly.setChecked(True)
        check_poly.toggled.connect(self.toggle_polygon_handles)
        layout_heat.addWidget(check_poly)
        
        layout_heat.addWidget(check_poly)
        
        layout_heat.addWidget(QLabel("Boundary Shape:"))
        combo_shape = QComboBox()
        combo_shape.addItems(["Custom Polygon", "Rectangle", "Circle"])
        combo_shape.currentTextChanged.connect(self.change_boundary_shape)
        layout_heat.addWidget(combo_shape)
        
        layout.addWidget(group_heat)
        
        # Data Table
        group_data = QGroupBox("Data Points")
        layout_data = QVBoxLayout(group_data)
        
        self.table_model = PointTableModel(self.data_container)
        self.table_model.dataChanged.connect(self.on_table_changed)
        
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setMinimumHeight(200)
        layout_data.addWidget(self.table_view)
        
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("Add Random")
        btn_add.clicked.connect(self.add_point)
        btn_layout.addWidget(btn_add)
        
        btn_del = QPushButton("Delete Selected")
        btn_del.clicked.connect(self.delete_selected_points)
        btn_layout.addWidget(btn_del)
        
        btn_regen = QPushButton("Regenerate")
        btn_regen.clicked.connect(self.generate_data)
        btn_layout.addWidget(btn_regen)
        
        layout_data.addLayout(btn_layout)
        layout.addWidget(group_data)
        
        dock.setWidget(widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

    def generate_data(self):
        df = generate_dummy_data(n_points=20)
        points = df[['x', 'y']].values
        values = df['value'].values
        labels = [f"P{i}" for i in range(len(points))]
        self.data_container.set_data(points, values, labels)

    def add_point(self):
        x = (np.random.rand() - 0.5) * 300
        y = (np.random.rand() - 0.5) * 300
        value = np.random.rand() * 100
        label = f"New"
        self.data_container.add_points([[x, y]], [value], [label])

    def delete_selected_points(self):
        rows = sorted(set(index.row() for index in self.table_view.selectedIndexes()), reverse=True)
        if rows:
            self.data_container.remove_points(rows)

    def on_table_changed(self, topLeft, bottomRight, roles):
        if Qt.ItemDataRole.CheckStateRole in roles:
            indices = self.table_model.get_highlighted_indices()
            self.value_layer.set_highlighted_indices(indices)
            self.label_layer.set_highlighted_indices(indices)

    def update_heatmap_polygon(self):
        self.heatmap_layer.set_boundary_shape(self.heatmap_polygon)
        self.update_polygon_handles()

    def update_polygon_handles(self):
        # Clear existing handles and edges
        for h in self.polygon_handles:
            self.scene.removeItem(h)
        self.polygon_handles.clear()
        
        for e in self.polygon_edges:
            self.scene.removeItem(e)
        self.polygon_edges.clear()
        
        count = self.heatmap_polygon.count()
        if count == 0: return

        # Create Edges first (so they are below handles)
        for i in range(count):
            p1 = self.heatmap_polygon.at(i)
            p2 = self.heatmap_polygon.at((i + 1) % count)
            edge = PolygonEdge(i, p1, p2, self.on_polygon_point_added)
            self.scene.addItem(edge)
            self.polygon_edges.append(edge)
        
        # Create Handles
        for i in range(count):
            pt = self.heatmap_polygon.at(i)
            handle = PolygonHandle(i, pt.x(), pt.y(), self.on_handle_moved, self.on_polygon_point_removed)
            self.scene.addItem(handle)
            self.polygon_handles.append(handle)

    def on_handle_moved(self, index, new_pos):
        self.heatmap_polygon[index] = new_pos
        self.heatmap_layer.set_boundary_shape(self.heatmap_polygon)
        # Update edges connected to this handle
        count = self.heatmap_polygon.count()
        
        # Edge starting at index
        edge1 = self.polygon_edges[index]
        edge1.setLine(new_pos.x(), new_pos.y(), edge1.line().x2(), edge1.line().y2())
        
        # Edge ending at index (previous edge)
        prev_index = (index - 1 + count) % count
        edge2 = self.polygon_edges[prev_index]
        edge2.setLine(edge2.line().x1(), edge2.line().y1(), new_pos.x(), new_pos.y())

    def on_polygon_point_added(self, index, pos):
        # Insert new point after index
        self.heatmap_polygon.insert(index + 1, pos)
        self.update_heatmap_polygon()

    def on_polygon_point_removed(self, index):
        if self.heatmap_polygon.count() <= 3:
            return # Keep at least 3 points
        self.heatmap_polygon.remove(index)
        self.update_heatmap_polygon()

    def toggle_polygon_handles(self, visible):
        for h in self.polygon_handles:
            h.setVisible(visible)
        for e in self.polygon_edges:
            e.setVisible(visible)

    def change_boundary_shape(self, shape_name):
        if shape_name == "Custom Polygon":
            self.heatmap_layer.set_boundary_shape(self.heatmap_polygon)
            self.toggle_polygon_handles(True)
        elif shape_name == "Rectangle":
            rect = QRectF(-200, -200, 400, 400)
            self.heatmap_layer.set_boundary_shape(rect)
            self.toggle_polygon_handles(False)
        elif shape_name == "Circle":
            path = QPainterPath()
            path.addEllipse(-200, -200, 400, 400)
            self.heatmap_layer.set_boundary_shape(path)
            self.toggle_polygon_handles(False)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AllLayersDemo()
    window.show()
    sys.exit(app.exec())
