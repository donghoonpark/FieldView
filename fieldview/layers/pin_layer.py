from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtCore import QPointF, Qt, QRectF
from fieldview.layers.data_layer import DataLayer

class PinLayer(DataLayer):
    """
    Layer for rendering icons (pins) at data points.
    """
    def __init__(self, data_container, parent=None):
        super().__init__(data_container, parent)
        self._icon = None
        self._icon_size = 24 # Default size

    @property
    def icon(self):
        return self._icon

    def set_icon(self, icon: QPixmap):
        self._icon = icon
        self.update_layer()

    def paint(self, painter, option, widget):
        if not self._icon:
            return
            
        points, _, _ = self.get_valid_data()
        
        # Scale icon if needed or use as is. 
        # For now, assume icon is pre-scaled or we draw it centered.
        w = self._icon.width()
        h = self._icon.height()
        
        for x, y in points:
            # Draw icon centered at (x, y)
            # Assuming pin tip is at bottom center? Or center?
            # Standard pin usually has tip at bottom center.
            # Let's assume center for generic icon, or provide an anchor.
            # For "Pin", usually bottom center.
            # Let's draw centered for now as per "icon".
            
            target_rect = QRectF(x - w/2, y - h/2, w, h)
            painter.drawPixmap(target_rect.toRect(), self._icon)
