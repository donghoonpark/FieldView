try:
    from qtpy.QtSvgWidgets import QGraphicsSvgItem
except ImportError:
    # PyQt5 compatibility
    from qtpy.QtSvg import QGraphicsSvgItem
