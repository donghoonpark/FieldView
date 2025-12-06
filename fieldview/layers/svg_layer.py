from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtSvg import QSvgRenderer
    from PySide6.QtCore import QRectF, QPointF
    from PySide6.QtGui import QPainter
    from PySide6.QtWidgets import QStyleOptionGraphicsItem, QWidget
else:
    from qtpy.QtSvg import QSvgRenderer
    from qtpy.QtCore import QRectF, QPointF
    from qtpy.QtGui import QPainter
    from qtpy.QtWidgets import QStyleOptionGraphicsItem, QWidget
from fieldview.layers.layer import Layer
from typing import Optional


class SvgLayer(Layer):
    """
    Layer for rendering an SVG file.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._renderer = QSvgRenderer()
        self._svg_path = ""
        self._origin = QPointF(0, 0)

    @property
    def svg_path(self):
        return self._svg_path

    @property
    def origin(self):
        return self._origin

    def set_origin(self, origin):
        """
        Sets the drawing origin (top-left corner) for the SVG within the scene.

        Args:
            origin (QPointF | tuple | list): Absolute origin in scene
                coordinates. Tuples/lists are interpreted as (x, y).
        """
        if isinstance(origin, (tuple, list)) and len(origin) == 2:
            origin = QPointF(float(origin[0]), float(origin[1]))
        elif isinstance(origin, QPointF):
            origin = QPointF(origin)  # make a defensive copy
        else:
            raise TypeError("origin must be a QPointF or a (x, y) tuple/list")

        if origin == self._origin:
            return

        self.prepareGeometryChange()
        self._origin = origin
        self.update_layer()

    def load_svg(self, path):
        """
        Loads an SVG file from the given path.
        """
        self._svg_path = path
        if self._renderer.load(path):
            self.set_bounding_rect(self._renderer.viewBoxF())
            self.update_layer()
        else:
            print(f"Failed to load SVG: {path}")

    def paint(
        self,
        painter: "QPainter",
        option: "QStyleOptionGraphicsItem",
        widget: Optional["QWidget"] = None,
    ) -> None:
        if self._renderer.isValid():
            # Render SVG to fit the bounding rect
            self._renderer.render(painter, self.boundingRect())

    def boundingRect(self):
        rect = QRectF(super().boundingRect())
        rect.translate(self._origin)
        return rect
