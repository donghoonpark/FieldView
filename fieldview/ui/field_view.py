from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPainter
else:
    from qtpy.QtWidgets import QGraphicsView, QGraphicsScene
    from qtpy.QtCore import Qt
    from qtpy.QtGui import QColor, QPainter

from fieldview.core.data_container import DataContainer
from fieldview.layers.heatmap_layer import HeatmapLayer
from fieldview.layers.text_layer import ValueLayer, LabelLayer
from fieldview.layers.svg_layer import SvgLayer
from fieldview.layers.pin_layer import PinLayer


class FieldView(QGraphicsView):
    """
    A high-level widget for visualizing field data.
    Integrates QGraphicsView, QGraphicsScene, and DataContainer.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Core components
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.data_container = DataContainer()

        # View settings
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QColor(30, 30, 30))

        # Keep track of layers
        self.layers = {}

    def set_data(self, points, values, labels=None):
        """Sets the data for the visualization."""
        self.data_container.set_data(points, values, labels)

    def add_heatmap_layer(self, opacity=0.6, z_value=0):
        """Adds a heatmap layer."""
        layer = HeatmapLayer(self.data_container)
        layer.setOpacity(opacity)
        layer.setZValue(z_value)
        self._scene.addItem(layer)
        self.layers["heatmap"] = layer
        return layer

    def add_svg_layer(self, file_path, z_value=-1):
        """Adds an SVG background layer."""
        layer = SvgLayer()
        layer.load_svg(file_path)
        layer.setZValue(z_value)
        self._scene.addItem(layer)
        self.layers["svg"] = layer
        return layer

    def add_pin_layer(self, z_value=10):
        """Adds a pin layer for data points."""
        layer = PinLayer(self.data_container)
        layer.setZValue(z_value)
        self._scene.addItem(layer)
        self.layers["pin"] = layer
        return layer

    def add_value_layer(self, z_value=5):
        """Adds a layer displaying value text."""
        layer = ValueLayer(self.data_container)
        layer.setZValue(z_value)
        self._scene.addItem(layer)
        self.layers["value"] = layer
        return layer

    def add_label_layer(self, z_value=5):
        """Adds a layer displaying label text."""
        layer = LabelLayer(self.data_container)
        layer.setZValue(z_value)
        self._scene.addItem(layer)
        self.layers["label"] = layer
        return layer

    def fit_to_scene(self):
        """Fits the view to the scene content."""
        self._scene.setSceneRect(self._scene.itemsBoundingRect())
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event):
        """Handles zoom on mouse wheel."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # If Ctrl is held, maybe do something else?
            # Standard behavior for many apps is just wheel to zoom, or Ctrl+wheel.
            # For now, let's make plain wheel zoom, as it's often expected in map viewers.
            pass

        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor

        # Save the scene pos
        if hasattr(event, "position"):
            pos = event.position().toPoint()
        else:
            pos = event.pos()
        old_pos = self.mapToScene(pos)

        # Zoom
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor

        self.scale(zoom_factor, zoom_factor)

        # Get the new position
        if hasattr(event, "position"):
            pos = event.position().toPoint()
        else:
            pos = event.pos()
        new_pos = self.mapToScene(pos)

        # Move scene to old position
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())
