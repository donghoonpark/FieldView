from PySide6.QtGui import QFont, QColor, QFontDatabase
from PySide6.QtCore import Qt, QRectF, QPointF
import os
from fieldview.layers.data_layer import DataLayer

class TextLayer(DataLayer):
    """
    Abstract base class for text-based layers.
    Handles font, opacity, and highlighting.
    """
    def __init__(self, data_container, parent=None):
        super().__init__(data_container, parent)
        
        # Load embedded font
        font_path = os.path.join(os.path.dirname(__file__), '..', 'resources', 'fonts', 'JetBrainsMono-Regular.ttf')
        font_path = os.path.abspath(font_path)
        
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
            self._font = QFont(font_family)
        else:
            # Fallback
            self._font = QFont("JetBrains Mono")
            if not QFontDatabase.families(QFontDatabase.WritingSystem.Latin).count("JetBrains Mono"):
                 self._font.setStyleHint(QFont.StyleHint.Monospace)
        
        self._font.setPixelSize(12)
        
        self._text_color = QColor(Qt.GlobalColor.white)
        self._bg_color = QColor(0, 0, 0, 180) # Semi-transparent black
        self._highlight_color = QColor(Qt.GlobalColor.yellow)
        self._highlighted_indices = set()
        
        self._collision_avoidance_enabled = False
        self._collision_offset_factor = 0.6 # Default 60%
        self._cached_layout = None

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

    @property
    def collision_avoidance_enabled(self):
        return self._collision_avoidance_enabled

    @collision_avoidance_enabled.setter
    def collision_avoidance_enabled(self, enabled):
        self._collision_avoidance_enabled = enabled
        self.update_layer()

    @property
    def collision_offset_factor(self):
        return self._collision_offset_factor

    @collision_offset_factor.setter
    def collision_offset_factor(self, factor):
        self._collision_offset_factor = factor
        self.update_layer()

    def update_layer(self):
        self._cached_layout = None
        super().update_layer()

    def paint(self, painter, option, widget):
        points, values, labels = self.get_valid_data()
        
        painter.setFont(self._font)
        metrics = painter.fontMetrics()
        
        if self._cached_layout is None:
            self._cached_layout = self._calculate_layout(points, values, labels, metrics)
            
        for i, rect in self._cached_layout.items():
            text = self._get_text(i, values[i], labels[i])
            if not text: continue
            
            # Determine background color
            bg_color = self._highlight_color if i in self._highlighted_indices else self._bg_color
            
            # Draw background
            painter.fillRect(rect, bg_color)
            
            # Draw text
            painter.setPen(self._text_color if i not in self._highlighted_indices else Qt.GlobalColor.black)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def _calculate_layout(self, points, values, labels, metrics):
        layout = {} # index -> QRectF
        placed_rects = []
        
        for i, (x, y) in enumerate(points):
            text = self._get_text(i, values[i], labels[i])
            if not text: continue
            
            rect = metrics.boundingRect(text)
            # Add padding
            rect.adjust(-2, -2, 2, 2)
            w, h = rect.width(), rect.height()
            
            # Calculate offset distance based on factor
            # Factor 0.6 means move 60% of dimension.
            # Center is 0 offset.
            # Top: y - h * factor
            # Bottom: y + h * factor
            # Left: x - w * factor
            # Right: x + w * factor
            
            factor = self._collision_offset_factor
            
            candidates = [
                QPointF(x, y), # Center
                QPointF(x, y - h * factor), # Top
                QPointF(x, y + h * factor), # Bottom
                QPointF(x - w * factor, y), # Left
                QPointF(x + w * factor, y)  # Right
            ]
            
            chosen_rect = None
            
            if self._collision_avoidance_enabled:
                for center in candidates:
                    candidate_rect = QRectF(rect)
                    candidate_rect.moveCenter(center)
                    
                    # Check collision
                    collision = False
                    for placed in placed_rects:
                        if candidate_rect.intersects(placed):
                            collision = True
                            break
                    
                    if not collision:
                        chosen_rect = candidate_rect
                        break
                
                # If all collide, fallback to Center (first candidate)
                if chosen_rect is None:
                     candidate_rect = QRectF(rect)
                     candidate_rect.moveCenter(candidates[0])
                     chosen_rect = candidate_rect
            else:
                # Just Center
                chosen_rect = QRectF(rect)
                chosen_rect.moveCenter(QPointF(x, y))
                
            layout[i] = chosen_rect
            placed_rects.append(chosen_rect)
            
        return layout

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
