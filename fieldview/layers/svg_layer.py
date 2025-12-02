from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QPainter
from PySide6.QtCore import QPointF, QRectF
from fieldview.layers.layer import Layer

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

    def load_svg(self, path):
        """
        Loads an SVG file from the given path.
        """
        self._svg_path = path
        if self._renderer.load(path):
            self._update_bounding_rect()
            self.update_layer()
        else:
            print(f"Failed to load SVG: {path}")

    def set_origin(self, origin):
        """
        Sets a manual origin offset for the SVG. The origin is applied to the
        SVG's viewbox so users can align floorplans when the embedded origin is
        misaligned.
        """
        if not isinstance(origin, QPointF):
            origin = QPointF(*origin)

        if origin == self._origin:
            return

        self._origin = origin
        self._update_bounding_rect()
        self.update_layer()

    def paint(self, painter, option, widget):
        if self._renderer.isValid():
            # Render SVG to fit the bounding rect
            self._renderer.render(painter, self.boundingRect())

    def _update_bounding_rect(self):
        if self._renderer.isValid():
            rect = self._renderer.viewBoxF()
        else:
            rect = self.boundingRect()

        translated_rect = QRectF(rect)
        translated_rect.translate(self._origin)
        self.set_bounding_rect(translated_rect)
