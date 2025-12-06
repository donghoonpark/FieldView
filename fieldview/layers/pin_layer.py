from qtpy.QtGui import QPixmap
from qtpy.QtCore import QRectF, QPointF, Qt
from fieldview.layers.data_layer import DataLayer


class PinLayer(DataLayer):
    """
    Layer for rendering icons (pins) at data points.
    """

    def __init__(self, data_container, parent=None):
        super().__init__(data_container, parent)
        self._icon = None
        self._icon_size = 24  # Default size

    @property
    def icon(self):
        return self._icon

    def set_icon(self, icon: QPixmap):
        self._icon = icon
        self.update_layer()

    def paint(self, painter, option, widget):
        points, _, _ = self.get_valid_data()

        if self._icon:
            w = self._icon.width()
            h = self._icon.height()
            for x, y in points:
                target_rect = QRectF(x - w / 2, y - h / 2, w, h)
                painter.drawPixmap(target_rect.toRect(), self._icon)
        else:
            # Default: Black dot
            painter.setBrush(Qt.GlobalColor.black)
            painter.setPen(Qt.NoPen)
            r = 3  # Radius
            for x, y in points:
                painter.drawEllipse(QPointF(x, y), r, r)
