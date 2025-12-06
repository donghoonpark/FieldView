from typing import TYPE_CHECKING, Optional, List, Dict, Set, Union

if TYPE_CHECKING:
    from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics, QFontDatabase
    from PySide6.QtCore import Qt, QRectF, QPointF
    from PySide6.QtWidgets import QStyleOptionGraphicsItem, QWidget
else:
    from qtpy.QtGui import QPainter, QColor, QFont, QFontMetrics, QFontDatabase
    from qtpy.QtCore import Qt, QRectF, QPointF
    from qtpy.QtWidgets import QStyleOptionGraphicsItem, QWidget
import os
import numpy as np
from fieldview.layers.data_layer import DataLayer


class TextLayer(DataLayer):
    """
    Abstract base class for text-based layers.
    Handles font, opacity, and highlighting.
    """

    def __init__(self, data_container, parent: Optional[DataLayer] = None):
        super().__init__(data_container, parent)

        # Load embedded font
        font_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "resources",
            "fonts",
            "JetBrainsMono-Regular.ttf",
        )
        font_path = os.path.abspath(font_path)

        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
            self._font = QFont(font_family)
        else:
            # Fallback
            self._font = QFont("JetBrains Mono")
            if not QFontDatabase.families(QFontDatabase.WritingSystem.Latin).count(
                "JetBrains Mono"
            ):
                self._font.setStyleHint(QFont.StyleHint.Monospace)

        self._font.setPixelSize(12)

        self._text_color = QColor(Qt.GlobalColor.white)
        self._bg_color = QColor(0, 0, 0, 180)  # Semi-transparent black
        self._highlight_color = QColor(Qt.GlobalColor.yellow)
        self._highlighted_indices: set[int] = set()

        self._collision_avoidance_enabled = True
        self._collision_offset_factor = 0.6  # Default 60%
        self._cached_layout: Optional[Dict[int, QRectF]] = None

    @property
    def font(self) -> QFont:
        return self._font

    @font.setter
    def font(self, value: QFont):
        self._font = value
        self.update_layer()

    @property
    def highlighted_indices(self) -> Set[int]:
        return self._highlighted_indices

    def set_highlighted_indices(self, indices: List[int]):
        self._highlighted_indices = set(indices)
        self.update_layer()

    @property
    def highlight_color(self) -> QColor:
        return self._highlight_color

    @highlight_color.setter
    def highlight_color(self, color: Union[QColor, str, Qt.GlobalColor]):
        if isinstance(color, (str, Qt.GlobalColor)):
            self._highlight_color = QColor(color)
        elif isinstance(color, QColor):
            self._highlight_color = color
        else:
            raise TypeError("Color must be QColor, str, or Qt.GlobalColor")
        self.update_layer()

    @property
    def collision_avoidance_enabled(self) -> bool:
        return self._collision_avoidance_enabled

    @collision_avoidance_enabled.setter
    def collision_avoidance_enabled(self, enabled: bool):
        self._collision_avoidance_enabled = enabled
        self.update_layer()

    @property
    def collision_offset_factor(self) -> float:
        return self._collision_offset_factor

    @collision_offset_factor.setter
    def collision_offset_factor(self, factor: float):
        self._collision_offset_factor = factor
        self.update_layer()

    def update_layer(self):
        self._cached_layout = None
        super().update_layer()

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: Optional[QWidget] = None,
    ):
        points, values, labels = self.get_valid_data()
        valid_indices = self.get_valid_indices()

        painter.setFont(self._font)
        metrics = painter.fontMetrics()

        if self._cached_layout is None:
            self._cached_layout = self._calculate_layout(
                points, values, labels, metrics, valid_indices
            )

        value_lookup = dict(zip(valid_indices, values)) if values is not None else {}
        label_lookup = dict(zip(valid_indices, labels)) if labels is not None else {}

        for i, rect in self._cached_layout.items():
            value = value_lookup.get(i)
            label = label_lookup.get(i, "")
            text = self._get_text(i, value, label)
            if not text:
                continue

            # Determine background color
            bg_color = (
                self._highlight_color
                if i in self._highlighted_indices
                else self._bg_color
            )

            # Draw background
            painter.fillRect(rect, bg_color)

            # Draw text
            painter.setPen(
                self._text_color
                if i not in self._highlighted_indices
                else Qt.GlobalColor.black
            )
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def _calculate_layout(
        self,
        points: np.ndarray,
        values: np.ndarray,
        labels: List[str],
        metrics: QFontMetrics,
        indices: List[int],
    ) -> Dict[int, QRectF]:
        layout = {}  # index -> QRectF
        placed_rects: List[QRectF] = []

        for i, (x, y), value, label in zip(indices, points, values, labels):
            text = self._get_text(i, value, label)
            if not text:
                continue

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
                QPointF(x, y),  # Center
                QPointF(x, y - h * factor),  # Top
                QPointF(x, y + h * factor),  # Bottom
                QPointF(x - w * factor, y),  # Left
                QPointF(x + w * factor, y),  # Right
            ]

            chosen_rect = None

            if self._collision_avoidance_enabled:
                best_rect = None
                min_cost = float("inf")

                for center in candidates:
                    candidate_rect = QRectF(rect)
                    candidate_rect.moveCenter(center)

                    # Calculate cost (total intersection area)
                    cost = 0.0
                    for placed in placed_rects:
                        intersection = candidate_rect.intersected(placed)
                        if not intersection.isEmpty():
                            cost += intersection.width() * intersection.height()

                    # If perfect placement found, take it immediately
                    if cost == 0:
                        best_rect = candidate_rect
                        break

                    # Otherwise keep track of the best so far
                    if cost < min_cost:
                        min_cost = cost
                        best_rect = candidate_rect

                chosen_rect = best_rect
            else:
                # Just Center
                chosen_rect = QRectF(rect)
                chosen_rect.moveCenter(QPointF(x, y))

            if chosen_rect is not None:
                layout[i] = chosen_rect
                placed_rects.append(chosen_rect)

        return layout

    def _get_text(self, index: int, value: Optional[float], label: str) -> str:
        """
        Abstract method to get text for a point.
        """
        raise NotImplementedError


class ValueLayer(TextLayer):
    """
    Renders numerical values.
    """

    def __init__(self, data_container, parent: Optional[DataLayer] = None):
        super().__init__(data_container, parent)
        self._decimal_places = 2
        self._suffix = ""
        self._postfix = ""  # Same as suffix? antigravity.md says both. Let's assume prefix/suffix or just suffix.
        # antigravity.md says "Can add suffix, postfix". Maybe prefix/suffix?
        # Let's implement prefix and suffix.
        self._prefix = ""

    @property
    def decimal_places(self) -> int:
        return self._decimal_places

    @decimal_places.setter
    def decimal_places(self, value: int):
        self._decimal_places = value
        self.update_layer()

    @property
    def suffix(self) -> str:
        return self._suffix

    @suffix.setter
    def suffix(self, value: str):
        self._suffix = value
        self.update_layer()

    @property
    def prefix(self) -> str:
        return self._prefix

    @prefix.setter
    def prefix(self, value: str):
        self._prefix = value
        self.update_layer()

    def _get_text(self, index: int, value: Optional[float], label: str) -> str:
        if value is None:
            return ""
        return f"{self._prefix}{value:.{self._decimal_places}f}{self._suffix}"


class LabelLayer(TextLayer):
    """
    Renders text labels.
    """

    def _get_text(self, index: int, value: Optional[float], label: str) -> str:
        return str(label)
