from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QPainter
from PySide6.QtCore import QRectF
from fieldview.layers.layer import Layer

class SvgLayer(Layer):
    """
    Layer for rendering an SVG file.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._renderer = QSvgRenderer()
        self._svg_path = ""

    @property
    def svg_path(self):
        return self._svg_path

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

    def paint(self, painter, option, widget):
        if self._renderer.isValid():
            # Render SVG to fit the bounding rect
            self._renderer.render(painter, self.boundingRect())
