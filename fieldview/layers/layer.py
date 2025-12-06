from qtpy.QtWidgets import QGraphicsObject, QStyleOptionGraphicsItem, QWidget
from qtpy.QtGui import QPainter
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from PySide6.QtCore import QRectF
    from PySide6.QtWidgets import QStyleOptionGraphicsItem, QWidget
    from PySide6.QtGui import QPainter
else:
    from qtpy.QtCore import QRectF
    from qtpy.QtWidgets import QStyleOptionGraphicsItem, QWidget
    from qtpy.QtGui import QPainter


class Layer(QGraphicsObject):
    """
    Abstract base class for all visual layers in FieldView.
    Inherits from QGraphicsObject to support signals and integration with QGraphicsScene.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bounding_rect = QRectF(
            0, 0, 300, 300
        )  # Default size, should be updated by subclasses

    def boundingRect(self):
        return self._bounding_rect

    def set_bounding_rect(self, rect):
        self._bounding_rect = rect
        self.prepareGeometryChange()
        self.update()

    def paint(
        self,
        painter: "QPainter",
        option: "QStyleOptionGraphicsItem",
        widget: Optional["QWidget"] = None,
    ) -> None:
        """
        Default paint implementation. Subclasses should override this.
        """
        pass

    def update_layer(self):
        """
        Triggers a layer update. Can be overridden to perform calculation before repaint.
        """
        self.update()
