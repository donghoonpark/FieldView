from PySide6.QtGui import QFont, QColor, QFontDatabase
from PySide6.QtCore import Qt, QRectF, QPointF
from fieldview.layers.data_layer import DataLayer

class TextLayer(DataLayer):
    """
    Abstract base class for text-based layers.
    Handles font, opacity, and highlighting.
    """
    def __init__(self, data_container, parent=None):
        super().__init__(data_container, parent)
        
        # Default Font (JetBrains Mono if available, else Monospace)
        self._font = QFont("JetBrains Mono")
        if not QFontDatabase.families(QFontDatabase.WritingSystem.Latin).count("JetBrains Mono"):
             self._font.setStyleHint(QFont.StyleHint.Monospace)
        self._font.setPixelSize(12)
        
        self._text_color = QColor(Qt.GlobalColor.white)
        self._bg_color = QColor(0, 0, 0, 180) # Semi-transparent black
        self._highlight_color = QColor(Qt.GlobalColor.yellow)
        self._highlighted_indices = set()

    @property
    def font(self):
        return self._font

    @font.setter
    def font(self, value):
        self._font = value
        self.update_layer()

    @property
    def highlighted_indices(self):
        return self._highlighted_indices

    def set_highlighted_indices(self, indices):
        self._highlighted_indices = set(indices)
        self.update_layer()

    def paint(self, painter, option, widget):
        points, values, labels = self.get_valid_data()
        
        painter.setFont(self._font)
        metrics = painter.fontMetrics()
        
        for i, (x, y) in enumerate(points):
            # Determine text to draw (implemented by subclasses)
            text = self._get_text(i, values[i], labels[i])
            if not text:
                continue
                
            # Determine background color
            bg_color = self._highlight_color if i in self._highlighted_indices else self._bg_color
            
            # Calculate rect
            rect = metrics.boundingRect(text)
            rect.moveCenter(QPointF(x, y).toPoint())
            # Add padding
            rect.adjust(-2, -2, 2, 2)
            
            # Draw background
            painter.fillRect(rect, bg_color)
            
            # Draw text
            painter.setPen(self._text_color if i not in self._highlighted_indices else Qt.GlobalColor.black)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def _get_text(self, index, value, label):
        """
        Abstract method to get text for a point.
        """
        raise NotImplementedError

class ValueLayer(TextLayer):
    """
    Renders numerical values.
    """
    def __init__(self, data_container, parent=None):
        super().__init__(data_container, parent)
        self._decimal_places = 2
        self._suffix = ""
        self._postfix = "" # Same as suffix? antigravity.md says both. Let's assume prefix/suffix or just suffix.
        # antigravity.md says "Can add suffix, postfix". Maybe prefix/suffix? 
        # Let's implement prefix and suffix.
        self._prefix = ""

    @property
    def decimal_places(self):
        return self._decimal_places

    @decimal_places.setter
    def decimal_places(self, value):
        self._decimal_places = value
        self.update_layer()

    @property
    def suffix(self):
        return self._suffix

    @suffix.setter
    def suffix(self, value):
        self._suffix = value
        self.update_layer()
        
    @property
    def prefix(self):
        return self._prefix

    @prefix.setter
    def prefix(self, value):
        self._prefix = value
        self.update_layer()

    def _get_text(self, index, value, label):
        return f"{self._prefix}{value:.{self._decimal_places}f}{self._suffix}"

class LabelLayer(TextLayer):
    """
    Renders text labels.
    """
    def _get_text(self, index, value, label):
        return str(label)
