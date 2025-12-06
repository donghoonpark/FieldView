from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtSvgWidgets import QGraphicsSvgItem
else:
    try:
        from qtpy.QtSvgWidgets import QGraphicsSvgItem
    except ImportError:
        # Fallback for older Qt versions or different bindings
        try:
            from qtpy.QtSvg import QGraphicsSvgItem as QGraphicsSvgItem
        except ImportError:
            pass
