import sys
import os
import numpy as np
import pandas as pd
from PySide6.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene, 
                               QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                               QCheckBox, QGroupBox, QSlider, QComboBox, QTableView, 
                               QHeaderView, QAbstractItemView, QGraphicsEllipseItem, QDockWidget, 
                               QGraphicsLineItem, QTreeWidget, QTreeWidgetItem, QDoubleSpinBox, 
                               QColorDialog, QSpinBox, QFrame)
from PySide6.QtGui import QPainterPath, QPainter, QPolygonF, QColor, QPixmap, QBrush, QPen, QStandardItemModel, QStandardItem, QFont
from PySide6.QtCore import Qt, QPointF, QAbstractTableModel, QModelIndex, Signal, QRectF, QTimer

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fieldview.core.data_container import DataContainer
from fieldview.layers.heatmap_layer import HeatmapLayer
from fieldview.layers.text_layer import ValueLayer, LabelLayer
from fieldview.layers.svg_layer import SvgLayer
from fieldview.layers.pin_layer import PinLayer
from fieldview.rendering.colormaps import COLORMAPS
from examples.generate_data import generate_dummy_data

# --- Property Browser Components ---

class PropertyBrowser(QTreeWidget):
    def __init__(self):
        super().__init__()
        self.setHeaderLabels(["Property", "Value"])
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

    def clear_properties(self):
        self.clear()

    def add_group(self, name):
        item = QTreeWidgetItem(self)
        item.setText(0, name)
        item.setExpanded(True)
        # Make group header bold
        font = item.font(0)
        font.setBold(True)
        item.setFont(0, font)
        return item

    def add_float_property(self, parent, name, value, setter, min_val=0.0, max_val=1.0, step=0.1, decimals=2):
        item = QTreeWidgetItem(parent)
        item.setText(0, name)
        
        spin = QDoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setSingleStep(step)
        spin.setDecimals(decimals)
        spin.setValue(value)
        # Remove frame for cleaner look in tree
        spin.setFrame(False)
        spin.valueChanged.connect(setter)
        
        self.setItemWidget(item, 1, spin)
        return item

    def add_int_property(self, parent, name, value, setter, min_val=0, max_val=100, step=1):
        item = QTreeWidgetItem(parent)
        item.setText(0, name)
        
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setSingleStep(step)
        spin.setValue(value)
        spin.setFrame(False)
        spin.valueChanged.connect(setter)
        
        self.setItemWidget(item, 1, spin)
        return item

    def add_bool_property(self, parent, name, value, setter):
        item = QTreeWidgetItem(parent)
        item.setText(0, name)
        
        check = QCheckBox()
        check.setChecked(value)
        check.toggled.connect(setter)
        
        # Center the checkbox
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(check)
        layout.addStretch()
        
        self.setItemWidget(item, 1, widget)
        return item

    def add_enum_property(self, parent, name, value, options, setter):
        item = QTreeWidgetItem(parent)
        item.setText(0, name)
        
        combo = QComboBox()
        combo.addItems(options)
        if value in options:
            combo.setCurrentText(value)
        combo.setFrame(False)
        combo.currentTextChanged.connect(setter)
        
        self.setItemWidget(item, 1, combo)
        return item

    def add_action_property(self, parent, name, button_text, callback):
        item = QTreeWidgetItem(parent)
        item.setText(0, name)
        
        btn = QPushButton(button_text)
        btn.clicked.connect(callback)
        
        self.setItemWidget(item, 1, btn)
        return item

# --- Data Table Model (Reused) ---

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
        if not index.isValid(): return None
        row, col = index.row(), index.column()
        
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            if col == 1: return f"{self._data_container.points[row][0]:.2f}"
            if col == 2: return f"{self._data_container.points[row][1]:.2f}"
            if col == 3: return f"{self._data_container.values[row]:.2f}"
            if col == 4: return self._data_container.labels[row]
            
        if role == Qt.ItemDataRole.CheckStateRole and col == 0:
            return Qt.CheckState.Checked if row in self._highlighted_indices else Qt.CheckState.Unchecked
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid(): return False
        row, col = index.row(), index.column()
        
        if role == Qt.ItemDataRole.CheckStateRole and col == 0:
            if value == Qt.CheckState.Checked.value: self._highlighted_indices.add(row)
            else: self._highlighted_indices.discard(row)
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
            except ValueError: return False
        return False

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return ["Highlight", "X", "Y", "Value", "Label"][section]
        return None

    def flags(self, index):
        flags = super().flags(index)
        if index.column() == 0: flags |= Qt.ItemFlag.ItemIsUserCheckable
        else: flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    def get_highlighted_indices(self):
        return list(self._highlighted_indices)

# --- Polygon Editor Helpers (Reused) ---

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
        else: super().mousePressEvent(event)

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
        else: super().mousePressEvent(event)

# --- Main Application ---

class DemoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FieldView Demo")
        self.resize(1400, 900)
        
        # 1. Setup Core
        self.data_container = DataContainer()
        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QColor(30, 30, 30))
        
        # 2. Setup Layers
        self.setup_layers()
        
        # 3. Setup View
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setCentralWidget(self.view)
        
        # 4. Initialize Polygon State (Before Properties Dock)
        self.polygon_handles = []
        self.polygon_edges = []
        self.heatmap_polygon = QPolygonF([
            QPointF(-200, -200), QPointF(200, -200),
            QPointF(200, 200), QPointF(-200, 200)
        ])
        self.update_heatmap_polygon()
        self.toggle_polygon_handles(False) # Hidden by default

        # 5. Setup Properties Dock
        self.setup_properties_dock()
        
        # 6. Initial Data
        self.generate_data()

    def setup_layers(self):
        # SVG
        self.svg_layer = SvgLayer()
        self.create_dummy_svg()
        self.scene.addItem(self.svg_layer)
        
        # Heatmap
        self.heatmap_layer = HeatmapLayer(self.data_container)
        self.heatmap_layer.setOpacity(0.6)
        self.scene.addItem(self.heatmap_layer)
        
        # Pins
        self.pin_layer = PinLayer(self.data_container)
        self.create_dummy_pin()
        self.scene.addItem(self.pin_layer)
        
        # Values
        self.value_layer = ValueLayer(self.data_container)
        self.value_layer.decimal_places = 1
        self.value_layer.suffix = "°C"
        self.scene.addItem(self.value_layer)
        
        # Labels
        self.label_layer = LabelLayer(self.data_container)
        self.label_layer.setVisible(False)
        self.scene.addItem(self.label_layer)

    def setup_properties_dock(self):
        dock = QDockWidget("Inspector", self)
        dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Render Time Label
        self.lbl_render_time = QLabel("Render Time: 0.00 ms")
        self.lbl_render_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_render_time)
        
        # Connect signal
        self.heatmap_layer.renderingFinished.connect(self.update_render_time)

        # Property Browser
        self.props = PropertyBrowser()
        layout.addWidget(self.props, stretch=1)
        
        # Data Table
        group_data = QGroupBox("Data Points")
        layout_data = QVBoxLayout(group_data)
        layout_data.setContentsMargins(0, 0, 0, 0)
        
        self.table_model = PointTableModel(self.data_container)
        self.table_model.dataChanged.connect(self.on_table_changed)
        
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
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
        layout.addWidget(group_data, stretch=0)
        
        # Simulation Controls
        group_sim = QGroupBox("Simulation")
        layout_sim = QVBoxLayout(group_sim)
        
        hbox_sim = QHBoxLayout()
        hbox_sim.addWidget(QLabel("Interval (ms):"))
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(10, 2000)
        self.spin_interval.setValue(50)
        hbox_sim.addWidget(self.spin_interval)
        layout_sim.addLayout(hbox_sim)
        
        hbox_noise = QHBoxLayout()
        hbox_noise.addWidget(QLabel("Noise Amt:"))
        self.spin_noise = QDoubleSpinBox()
        self.spin_noise.setRange(0.0, 50.0)
        self.spin_noise.setValue(5.0)
        hbox_noise.addWidget(self.spin_noise)
        layout_sim.addLayout(hbox_noise)
        
        self.btn_sim = QPushButton("Start Noise")
        self.btn_sim.setCheckable(True)
        self.btn_sim.toggled.connect(self.toggle_simulation)
        layout_sim.addWidget(self.btn_sim)
        
        layout.addWidget(group_sim)
        
        dock.setWidget(widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        
        # Populate all properties
        self.populate_all_properties()

    def populate_all_properties(self):
        self.props.clear_properties()
        self.populate_heatmap_properties()
        self.populate_value_properties()
        self.populate_label_properties()
        self.populate_pin_properties()
        self.populate_svg_properties()

    def populate_heatmap_properties(self):
        root = self.props.add_group("Heatmap Layer")
        self.props.add_bool_property(root, "Visible", self.heatmap_layer.isVisible(), self.heatmap_layer.setVisible)
        self.props.add_float_property(root, "Opacity", self.heatmap_layer.opacity(), self.heatmap_layer.setOpacity, step=0.05)
        self.props.add_enum_property(root, "Colormap", self.heatmap_layer.colormap, list(COLORMAPS.keys()), 
                                     lambda n: setattr(self.heatmap_layer, 'colormap', n))
        
        self.props.add_enum_property(root, "Boundary Shape", "Custom Polygon", ["Custom Polygon", "Rectangle", "Circle"], 
                                     self.change_boundary_shape)
        self.props.add_bool_property(root, "Edit Polygon", self.polygon_handles[0].isVisible() if self.polygon_handles else False, 
                                     self.toggle_polygon_handles)

    def populate_value_properties(self):
        root = self.props.add_group("Value Layer")
        self.props.add_bool_property(root, "Visible", self.value_layer.isVisible(), self.value_layer.setVisible)
        self.props.add_float_property(root, "Opacity", self.value_layer.opacity(), self.value_layer.setOpacity, step=0.05)
        self.props.add_int_property(root, "Font Size", self.value_layer.font.pixelSize(), 
                                    lambda s: self.set_layer_font_size(self.value_layer, s), min_val=6, max_val=72)
        self.props.add_int_property(root, "Decimals", self.value_layer.decimal_places, 
                                    lambda d: setattr(self.value_layer, 'decimal_places', d), min_val=0, max_val=5)
        self.props.add_bool_property(root, "Avoid Collisions", self.value_layer.collision_avoidance_enabled, 
                                     lambda b: setattr(self.value_layer, 'collision_avoidance_enabled', b))
        self.props.add_float_property(root, "Offset Factor", self.value_layer.collision_offset_factor, 
                                      lambda f: setattr(self.value_layer, 'collision_offset_factor', f), min_val=0.5, max_val=2.0)

    def populate_label_properties(self):
        root = self.props.add_group("Label Layer")
        self.props.add_bool_property(root, "Visible", self.label_layer.isVisible(), self.label_layer.setVisible)
        self.props.add_float_property(root, "Opacity", self.label_layer.opacity(), self.label_layer.setOpacity, step=0.05)
        self.props.add_int_property(root, "Font Size", self.label_layer.font.pixelSize(), 
                                    lambda s: self.set_layer_font_size(self.label_layer, s), min_val=6, max_val=72)
        self.props.add_bool_property(root, "Avoid Collisions", self.label_layer.collision_avoidance_enabled, 
                                     lambda b: setattr(self.label_layer, 'collision_avoidance_enabled', b))
        self.props.add_float_property(root, "Offset Factor", self.label_layer.collision_offset_factor, 
                                      lambda f: setattr(self.label_layer, 'collision_offset_factor', f), min_val=0.5, max_val=2.0)

    def populate_pin_properties(self):
        root = self.props.add_group("Pin Layer")
        self.props.add_bool_property(root, "Visible", self.pin_layer.isVisible(), self.pin_layer.setVisible)
        self.props.add_float_property(root, "Opacity", self.pin_layer.opacity(), self.pin_layer.setOpacity, step=0.05)

    def populate_svg_properties(self):
        root = self.props.add_group("SVG Layer")
        self.props.add_bool_property(root, "Visible", self.svg_layer.isVisible(), self.svg_layer.setVisible)
        self.props.add_float_property(root, "Opacity", self.svg_layer.opacity(), self.svg_layer.setOpacity, step=0.05)

    def set_layer_font_size(self, layer, size):
        font = layer.font
        font.setPixelSize(size)
        layer.font = font

    # --- Logic Methods (Reused) ---

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
        with open(filename, "wb") as f: f.write(svg_content)
        self.svg_layer.load_svg(filename)

    def create_dummy_pin(self):
        # Create a simple black dot
        pixmap = QPixmap(10, 10)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(Qt.GlobalColor.black))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 10, 10)
        painter.end()
        self.pin_layer.set_icon(pixmap)

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
        self.data_container.add_points([[x, y]], [value], ["New"])

    def delete_selected_points(self):
        rows = sorted(set(index.row() for index in self.table_view.selectedIndexes()), reverse=True)
        if rows: self.data_container.remove_points(rows)

    def on_table_changed(self, topLeft, bottomRight, roles):
        if Qt.ItemDataRole.CheckStateRole in roles:
            indices = self.table_model.get_highlighted_indices()
            self.value_layer.set_highlighted_indices(indices)
            self.label_layer.set_highlighted_indices(indices)

    def update_heatmap_polygon(self):
        self.heatmap_layer.set_boundary_shape(self.heatmap_polygon)
        self.update_polygon_handles()

    def update_polygon_handles(self):
        for h in self.polygon_handles: self.scene.removeItem(h)
        self.polygon_handles.clear()
        for e in self.polygon_edges: self.scene.removeItem(e)
        self.polygon_edges.clear()
        
        count = self.heatmap_polygon.count()
        if count == 0: return

        for i in range(count):
            p1 = self.heatmap_polygon.at(i)
            p2 = self.heatmap_polygon.at((i + 1) % count)
            edge = PolygonEdge(i, p1, p2, self.on_polygon_point_added)
            self.scene.addItem(edge)
            self.polygon_edges.append(edge)
        
        for i in range(count):
            pt = self.heatmap_polygon.at(i)
            handle = PolygonHandle(i, pt.x(), pt.y(), self.on_handle_moved, self.on_polygon_point_removed)
            self.scene.addItem(handle)
            self.polygon_handles.append(handle)

    def on_handle_moved(self, index, new_pos):
        self.heatmap_polygon[index] = new_pos
        self.heatmap_layer.set_boundary_shape(self.heatmap_polygon)
        count = self.heatmap_polygon.count()
        edge1 = self.polygon_edges[index]
        edge1.setLine(new_pos.x(), new_pos.y(), edge1.line().x2(), edge1.line().y2())
        prev_index = (index - 1 + count) % count
        edge2 = self.polygon_edges[prev_index]
        edge2.setLine(edge2.line().x1(), edge2.line().y1(), new_pos.x(), new_pos.y())

    def on_polygon_point_added(self, index, pos):
        self.heatmap_polygon.insert(index + 1, pos)
        self.update_heatmap_polygon()

    def on_polygon_point_removed(self, index):
        if self.heatmap_polygon.count() <= 3: return
        self.heatmap_polygon.remove(index)
        self.update_heatmap_polygon()

    def toggle_polygon_handles(self, visible):
        for h in self.polygon_handles: h.setVisible(visible)
        for e in self.polygon_edges: e.setVisible(visible)

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
            
    def wheelEvent(self, event):
        factor = 1.1
        if event.angleDelta().y() < 0: factor = 1.0 / factor
        self.view.scale(factor, factor)

    def update_render_time(self, duration_ms):
        self.lbl_render_time.setText(f"Render Time: {duration_ms:.2f} ms")
        
    def toggle_simulation(self, checked):
        if checked:
            self.btn_sim.setText("Stop Noise")
            if not hasattr(self, 'sim_timer'):
                self.sim_timer = QTimer()
                self.sim_timer.timeout.connect(self.apply_noise)
            self.sim_timer.setInterval(self.spin_interval.value())
            self.sim_timer.start()
        else:
            self.btn_sim.setText("Start Noise")
            if hasattr(self, 'sim_timer'):
                self.sim_timer.stop()
                
    def apply_noise(self):
        amount = self.spin_noise.value()
        points = self.data_container.points
        values = self.data_container.values
        
        # Add noise to values
        noise = (np.random.rand(len(values)) - 0.5) * amount
        new_values = values + noise
        
        # Clamp values to 0-100 for sanity
        new_values = np.clip(new_values, 0, 100)
        
        # Update data container in batch? 
        # DataContainer doesn't have batch update for values only, 
        # but set_data does.
        self.data_container.set_data(points, new_values, self.data_container.labels)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DemoApp()
    window.show()
    sys.exit(app.exec())
