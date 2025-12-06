import sys
import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import (
        QApplication,
        QMainWindow,
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QSpinBox,
        QDoubleSpinBox,
        QComboBox,
        QCheckBox,
        QPushButton,
        QHeaderView,
        QLabel,
        QTreeWidget,
        QTreeWidgetItem,
        QGraphicsEllipseItem,
        QGraphicsLineItem,
        QAbstractItemView,
        QLineEdit,
        QColorDialog,
        QGraphicsView,
        QGraphicsScene,
    )
    from PySide6.QtGui import (
        QPainter,
        QBrush,
        QPen,
        QColor,
        QPolygonF,
        QPainterPath,
    )
    from PySide6.QtCore import QTimer, QPointF, QRectF, Qt
else:
    from qtpy.QtWidgets import (
        QApplication,
        QMainWindow,
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QSpinBox,
        QDoubleSpinBox,
        QComboBox,
        QCheckBox,
        QPushButton,
        QHeaderView,
        QLabel,
        QTreeWidget,
        QTreeWidgetItem,
        QGraphicsEllipseItem,
        QGraphicsLineItem,
        QAbstractItemView,
        QLineEdit,
        QColorDialog,
        QGraphicsView,
        QGraphicsScene,
    )
    from qtpy.QtGui import (
        QPainter,
        QBrush,
        QPen,
        QColor,
        QPolygonF,
        QPainterPath,
    )
    from qtpy.QtCore import QTimer, QPointF, QRectF, Qt

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fieldview.core.data_container import DataContainer
from fieldview.layers.heatmap_layer import HeatmapLayer
from fieldview.layers.text_layer import ValueLayer, LabelLayer
from fieldview.layers.svg_layer import SvgLayer
from fieldview.layers.pin_layer import PinLayer
from fieldview.rendering.colormaps import COLORMAPS
from fieldview.ui import ColorRangeControl
from fieldview.ui.data_table import DataTable
from examples.us_map_utils import (
    get_state_data,
    get_us_boundary,
    load_weather_data,
    generate_us_dataset,
)

# Import QtAds
import PySide6QtAds as ads

import numpy as np
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

    def add_float_property(
        self,
        parent,
        name,
        value,
        setter,
        min_val=0.0,
        max_val=1.0,
        step=0.1,
        decimals=2,
    ):
        item = QTreeWidgetItem(parent)
        item.setText(0, name)

        spin = QDoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setSingleStep(step)
        spin.setDecimals(decimals)
        spin.setValue(value)
        spin.setFrame(False)
        spin.valueChanged.connect(setter)

        self.setItemWidget(item, 1, spin)
        return item

    def add_int_property(
        self, parent, name, value, setter, min_val=0, max_val=100, step=1
    ):
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

        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
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

    def add_string_property(self, parent, name, value, setter):
        item = QTreeWidgetItem(parent)
        item.setText(0, name)

        edit = QLineEdit(value)
        edit.setFrame(False)
        edit.textChanged.connect(setter)

        self.setItemWidget(item, 1, edit)
        return item

    def add_color_property(self, parent, name, value, setter):
        item = QTreeWidgetItem(parent)
        item.setText(0, name)

        btn = QPushButton()
        btn.setFlat(True)

        def update_btn_color(color):
            btn.setStyleSheet(
                f"background-color: {color.name()}; border: 1px solid gray;"
            )

        update_btn_color(value)

        def pick_color():
            color = QColorDialog.getColor(value, None, f"Select {name}")
            if color.isValid():
                update_btn_color(color)
                setter(color)

        btn.clicked.connect(pick_color)
        self.setItemWidget(item, 1, btn)
        return item

    def add_action_property(self, parent, name, button_text, callback):
        item = QTreeWidgetItem(parent)
        item.setText(0, name)

        btn = QPushButton(button_text)
        btn.clicked.connect(callback)

        self.setItemWidget(item, 1, btn)
        return item


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


# --- Main Application ---


class DemoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FieldView Demo (QtAds)")
        self.resize(1600, 900)

        # 1. Setup Core
        self.data_container = DataContainer()
        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QColor(30, 30, 30))

        # 2. Setup Layers
        self.setup_layers()

        self._using_auto_range = True

        # 3. Setup Dock Manager
        self.dock_manager = ads.CDockManager(self)

        # 4. Setup View Dock
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        self.dock_view = ads.CDockWidget("Viewport")
        self.dock_view.setWidget(self.view)
        self.dock_manager.addDockWidget(
            ads.DockWidgetArea.CenterDockWidgetArea, self.dock_view
        )

        # 5. Initialize Polygon State
        self.polygon_handles = []
        self.polygon_edges = []
        self.heatmap_polygon = QPolygonF()
        self.heatmap_polygon.append(QPointF(-450, -330))
        self.heatmap_polygon.append(QPointF(-300, -330))
        self.heatmap_polygon.append(QPointF(-300, -250))
        self.heatmap_polygon.append(QPointF(-150, -250))
        self.heatmap_polygon.append(QPointF(-150, -300))
        self.heatmap_polygon.append(QPointF(150, -300))
        self.heatmap_polygon.append(QPointF(150, -250))
        self.heatmap_polygon.append(QPointF(450, -250))
        self.heatmap_polygon.append(QPointF(450, 250))
        self.heatmap_polygon.append(QPointF(-450, 250))
        self.update_heatmap_polygon()
        self.toggle_polygon_handles(False)

        # 6. Setup Other Docks
        self.setup_properties_dock()
        self.setup_data_dock()
        self.setup_simulation_dock()
        self.setup_color_dock()

        self.data_container.dataChanged.connect(self._handle_data_changed)

        # 7. Initial Data
        self.init_data()

    def setup_layers(self):
        # SVG
        self.svg_layer = SvgLayer()
        svg_path = os.path.join(os.path.dirname(__file__), "us_map.svg")
        self.svg_layer.load_svg(svg_path)
        self.scene.addItem(self.svg_layer)

        # Heatmap
        self.heatmap_layer = HeatmapLayer(self.data_container)
        self.heatmap_layer.setOpacity(0.6)
        self.scene.addItem(self.heatmap_layer)

        # Pins
        self.pin_layer = PinLayer(self.data_container)
        # self.create_dummy_pin() # Removed dummy pin
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
        self.dock_props = ads.CDockWidget("Inspector")
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Render Time Label
        self.lbl_render_time = QLabel("Render Time: 0.00 ms")
        self.lbl_render_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_render_time)

        self.heatmap_layer.renderingFinished.connect(self.update_render_time)

        # Property Browser
        self.props = PropertyBrowser()
        layout.addWidget(self.props)

        self.dock_props.setWidget(widget)
        self.dock_manager.addDockWidget(
            ads.DockWidgetArea.RightDockWidgetArea, self.dock_props
        )

        self.populate_all_properties()

    def setup_data_dock(self):
        self.dock_data = ads.CDockWidget("Data Points")
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.table_view = DataTable(self.data_container)
        self.table_model = self.table_view.table_model
        self.table_model.dataChanged.connect(self.on_table_changed)

        layout.addWidget(self.table_view)

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

        layout.addLayout(btn_layout)

        self.dock_data.setWidget(widget)
        # Split Inspector vertically, putting Data Points at the bottom
        self.dock_manager.addDockWidget(
            ads.DockWidgetArea.BottomDockWidgetArea,
            self.dock_data,
            self.dock_props.dockAreaWidget(),
        )

    def setup_simulation_dock(self):
        self.dock_sim = ads.CDockWidget("Simulation")
        widget = QWidget()
        layout = QVBoxLayout(widget)

        hbox_sim = QHBoxLayout()
        hbox_sim.addWidget(QLabel("Interval (ms):"))
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(10, 2000)
        self.spin_interval.setValue(50)
        hbox_sim.addWidget(self.spin_interval)
        layout.addLayout(hbox_sim)

        hbox_noise = QHBoxLayout()
        hbox_noise.addWidget(QLabel("Noise Amt:"))
        self.spin_noise = QDoubleSpinBox()
        self.spin_noise.setRange(0.0, 50.0)
        self.spin_noise.setValue(5.0)
        hbox_noise.addWidget(self.spin_noise)
        layout.addLayout(hbox_noise)

        self.btn_sim = QPushButton("Start Noise")
        self.btn_sim.setCheckable(True)
        self.btn_sim.toggled.connect(self.toggle_simulation)
        layout.addWidget(self.btn_sim)

        layout.addStretch()

        self.dock_sim.setWidget(widget)
        # Tabify with Data Points
        self.dock_manager.addDockWidget(
            ads.DockWidgetArea.CenterDockWidgetArea,
            self.dock_sim,
            self.dock_data.dockAreaWidget(),
        )

    def setup_color_dock(self):
        self.dock_color = ads.CDockWidget("Color Range")
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.color_range_control = ColorRangeControl(self.heatmap_layer.colormap)
        self.color_range_control.colorRangeChanged.connect(self.apply_color_range)
        layout.addWidget(self.color_range_control)

        btn_auto_range = QPushButton("Auto (Data Min/Max)")
        btn_auto_range.clicked.connect(self.reset_auto_color_range)
        layout.addWidget(btn_auto_range)

        layout.addStretch()

        self.dock_color.setWidget(widget)
        # Tabify with Data Points
        self.dock_manager.addDockWidget(
            ads.DockWidgetArea.CenterDockWidgetArea,
            self.dock_color,
            self.dock_data.dockAreaWidget(),
        )

    def populate_all_properties(self):
        self.props.clear_properties()
        self.populate_heatmap_properties()
        self.populate_value_properties()
        self.populate_label_properties()
        self.populate_pin_properties()
        self.populate_svg_properties()

    def populate_heatmap_properties(self):
        root = self.props.add_group("Heatmap Layer")
        self.props.add_bool_property(
            root,
            "Visible",
            self.heatmap_layer.isVisible(),
            self.heatmap_layer.setVisible,
        )
        self.props.add_float_property(
            root,
            "Opacity",
            self.heatmap_layer.opacity(),
            self.heatmap_layer.setOpacity,
            step=0.05,
        )
        self.props.add_enum_property(
            root,
            "Colormap",
            self.heatmap_layer.colormap,
            list(COLORMAPS.keys()),
            self._set_heatmap_colormap,
        )

        self.props.add_enum_property(
            root,
            "Quality",
            self.heatmap_layer.quality.title(),
            ["Very Low", "Low", "Medium", "High", "Very High", "Adaptive"],
            lambda q: setattr(self.heatmap_layer, "quality", q),
        )

        self.props.add_int_property(
            root,
            "Neighbors",
            self.heatmap_layer.neighbors,
            lambda n: setattr(self.heatmap_layer, "neighbors", n),
            min_val=1,
            max_val=100,
        )

        self.props.add_enum_property(
            root,
            "Boundary Shape",
            "Custom Polygon",
            ["Custom Polygon", "Rectangle", "Circle"],
            self.change_boundary_shape,
        )
        self.props.add_bool_property(
            root,
            "Edit Polygon",
            self.polygon_handles[0].isVisible() if self.polygon_handles else False,
            self.toggle_polygon_handles,
        )

    def _set_heatmap_colormap(self, name: str):
        self.heatmap_layer.colormap = name
        if hasattr(self, "color_range_control"):
            self.color_range_control.set_colormap(name)

    def populate_value_properties(self):
        root = self.props.add_group("Value Layer")
        self.props.add_bool_property(
            root, "Visible", self.value_layer.isVisible(), self.value_layer.setVisible
        )
        self.props.add_float_property(
            root,
            "Opacity",
            self.value_layer.opacity(),
            self.value_layer.setOpacity,
            step=0.05,
        )
        self.props.add_int_property(
            root,
            "Font Size",
            self.value_layer.font.pixelSize(),
            lambda s: self.set_layer_font_size(self.value_layer, s),
            min_val=6,
            max_val=72,
        )
        self.props.add_int_property(
            root,
            "Decimals",
            self.value_layer.decimal_places,
            lambda d: setattr(self.value_layer, "decimal_places", d),
            min_val=0,
            max_val=5,
        )

        self.props.add_string_property(
            root,
            "Prefix",
            self.value_layer.prefix,
            lambda s: setattr(self.value_layer, "prefix", s),
        )
        self.props.add_string_property(
            root,
            "Suffix",
            self.value_layer.suffix,
            lambda s: setattr(self.value_layer, "suffix", s),
        )

        self.props.add_color_property(
            root,
            "Highlight Color",
            self.value_layer.highlight_color,
            lambda c: setattr(self.value_layer, "highlight_color", c),
        )

        self.props.add_bool_property(
            root,
            "Avoid Collisions",
            self.value_layer.collision_avoidance_enabled,
            lambda b: setattr(self.value_layer, "collision_avoidance_enabled", b),
        )
        self.props.add_float_property(
            root,
            "Offset Factor",
            self.value_layer.collision_offset_factor,
            lambda f: setattr(self.value_layer, "collision_offset_factor", f),
            min_val=0.5,
            max_val=2.0,
        )

    def populate_label_properties(self):
        root = self.props.add_group("Label Layer")
        self.props.add_bool_property(
            root, "Visible", self.label_layer.isVisible(), self.label_layer.setVisible
        )
        self.props.add_float_property(
            root,
            "Opacity",
            self.label_layer.opacity(),
            self.label_layer.setOpacity,
            step=0.05,
        )
        self.props.add_int_property(
            root,
            "Font Size",
            self.label_layer.font.pixelSize(),
            lambda s: self.set_layer_font_size(self.label_layer, s),
            min_val=6,
            max_val=72,
        )

        self.props.add_color_property(
            root,
            "Highlight Color",
            self.label_layer.highlight_color,
            lambda c: setattr(self.label_layer, "highlight_color", c),
        )

        self.props.add_bool_property(
            root,
            "Avoid Collisions",
            self.label_layer.collision_avoidance_enabled,
            lambda b: setattr(self.label_layer, "collision_avoidance_enabled", b),
        )
        self.props.add_float_property(
            root,
            "Offset Factor",
            self.label_layer.collision_offset_factor,
            lambda f: setattr(self.label_layer, "collision_offset_factor", f),
            min_val=0.5,
            max_val=2.0,
        )

    def populate_pin_properties(self):
        root = self.props.add_group("Pin Layer")
        self.props.add_bool_property(
            root, "Visible", self.pin_layer.isVisible(), self.pin_layer.setVisible
        )
        self.props.add_float_property(
            root,
            "Opacity",
            self.pin_layer.opacity(),
            self.pin_layer.setOpacity,
            step=0.05,
        )

    def populate_svg_properties(self):
        root = self.props.add_group("SVG Layer")
        self.props.add_bool_property(
            root, "Visible", self.svg_layer.isVisible(), self.svg_layer.setVisible
        )
        self.props.add_float_property(
            root,
            "Opacity",
            self.svg_layer.opacity(),
            self.svg_layer.setOpacity,
            step=0.05,
        )
        self.props.add_float_property(
            root,
            "Origin X",
            self.svg_layer.origin.x(),
            lambda x: self.set_svg_origin(x=x),
            min_val=-1000,
            max_val=1000,
            step=1.0,
            decimals=1,
        )
        self.props.add_float_property(
            root,
            "Origin Y",
            self.svg_layer.origin.y(),
            lambda y: self.set_svg_origin(y=y),
            min_val=-1000,
            max_val=1000,
            step=1.0,
            decimals=1,
        )

    def set_layer_font_size(self, layer, size):
        font = layer.font
        font.setPixelSize(size)
        layer.font = font

    def set_svg_origin(self, x=None, y=None):
        origin = self.svg_layer.origin
        new_x = origin.x() if x is None else x
        new_y = origin.y() if y is None else y
        self.svg_layer.set_origin((new_x, new_y))

    # --- Logic Methods (Reused) ---

    def generate_data(self):
        # Regenerate data (reload weather or generate random if needed)
        # For now, just re-initialize which reloads everything
        self.init_data()

    def add_point(self):
        # Re-use room definitions
        rooms = [
            (-450, -250, -150, 250),
            (-450, -330, -300, -250),
            (-150, -250, 150, 250),
            (-150, -300, 150, -250),
            (150, -250, 300, 0),
            (150, 0, 300, 250),
            (300, -250, 450, -100),
            (300, -100, 450, 250),
        ]
        room = rooms[np.random.randint(len(rooms))]
        x1, y1, x2, y2 = room
        margin = 10
        x = np.random.uniform(x1 + margin, x2 - margin)
        y = np.random.uniform(y1 + margin, y2 - margin)
        value = np.random.uniform(15, 35)
        self.data_container.add_points([[x, y]], [value], ["New"])

    def delete_selected_points(self):
        rows = sorted(
            set(index.row() for index in self.table_view.selectedIndexes()),
            reverse=True,
        )
        if rows:
            self.data_container.remove_points(rows)

    def on_table_changed(self, topLeft, bottomRight, roles):
        if Qt.ItemDataRole.CheckStateRole in roles:
            indices = self.table_model.get_highlighted_indices()
            self.value_layer.set_highlighted_indices(indices)
            self.label_layer.set_highlighted_indices(indices)
            excluded = self.table_model.get_excluded_indices()
            self.heatmap_layer.set_excluded_indices(excluded)
            self.value_layer.set_excluded_indices(excluded)
            self.label_layer.set_excluded_indices(excluded)
            self.pin_layer.set_excluded_indices(excluded)

    def update_heatmap_polygon(self):
        self.heatmap_layer.set_boundary_shape(self.heatmap_polygon)
        self.update_polygon_handles()

    def update_polygon_handles(self):
        for h in self.polygon_handles:
            self.scene.removeItem(h)
        self.polygon_handles.clear()
        for e in self.polygon_edges:
            self.scene.removeItem(e)
        self.polygon_edges.clear()

        count = self.heatmap_polygon.count()
        if count == 0:
            return

        for i in range(count):
            p1 = self.heatmap_polygon.at(i)
            p2 = self.heatmap_polygon.at((i + 1) % count)
            edge = PolygonEdge(i, p1, p2, self.on_polygon_point_added)
            self.scene.addItem(edge)
            self.polygon_edges.append(edge)

        for i in range(count):
            pt = self.heatmap_polygon.at(i)
            handle = PolygonHandle(
                i, pt.x(), pt.y(), self.on_handle_moved, self.on_polygon_point_removed
            )
            self.scene.addItem(handle)
            self.polygon_handles.append(handle)

    def on_handle_moved(self, index, new_pos):
        # QPolygonF modification workaround for PySide6
        points = [
            self.heatmap_polygon.at(i) for i in range(self.heatmap_polygon.count())
        ]
        points[index] = new_pos
        self.heatmap_polygon = QPolygonF(points)
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
        if self.heatmap_polygon.count() <= 3:
            return
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

    def apply_color_range(self, color_min: float, color_max: float):
        self._using_auto_range = False
        self.heatmap_layer.set_color_range(color_min, color_max)

    def reset_auto_color_range(self):
        self._using_auto_range = True
        self.heatmap_layer.set_color_range(None, None)
        self._update_color_range_from_data()

    def _handle_data_changed(self):
        if self._using_auto_range:
            self.heatmap_layer.set_color_range(None, None)
            self._update_color_range_from_data()

    def _update_color_range_from_data(self):
        if not hasattr(self, "color_range_control"):
            return

        values = self.data_container.values
        if values.size == 0:
            color_min, color_max = 0.0, 1.0
        else:
            color_min = float(values.min())
            color_max = float(values.max())

        self.color_range_control.set_range(color_min, color_max, emit_signal=False)

    def wheelEvent(self, event):
        factor = 1.1
        if event.angleDelta().y() < 0:
            factor = 1.0 / factor
        self.view.scale(factor, factor)

    def update_render_time(self, duration_ms, grid_size=0):
        self.lbl_render_time.setText(
            f"Render Time: {duration_ms:.2f} ms (Grid: {grid_size})"
        )

    def toggle_simulation(self, checked):
        if checked:
            self.btn_sim.setText("Stop Noise")
            if not hasattr(self, "sim_timer"):
                self.sim_timer = QTimer()
                self.sim_timer.timeout.connect(self.apply_noise)
            self.sim_timer.setInterval(self.spin_interval.value())
            self.sim_timer.start()
        else:
            self.btn_sim.setText("Start Noise")
            if hasattr(self, "sim_timer"):
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

        self.data_container.set_data(points, new_values, self.data_container.labels)

    def init_data(self):
        # Load US Map Data
        svg_file = os.path.join(os.path.dirname(__file__), "us_map.svg")
        state_paths, centroids = get_state_data(svg_file)

        # Setup Heatmap Boundary
        us_boundary = get_us_boundary(state_paths)
        self.heatmap_layer.set_boundary_shape(us_boundary)

        # Load Weather Data
        weather_data = load_weather_data()

        # Generate Dataset
        points, values = generate_us_dataset(centroids, weather_data)

        self.data_container.set_data(points, values)

        # Configure Heatmap Defaults for US Map
        self.heatmap_layer.neighbors = 100
        self.heatmap_layer.kernel = ""
        self.heatmap_layer.setOpacity(0.6)

        # Update Inspector
        # (Ideally we would update the property browser values here to match)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DemoApp()
    window.show()
    sys.exit(app.exec())
