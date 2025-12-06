try:
    from qtpy.QtSvgWidgets import QGraphicsSvgItem as QGraphicsSvgItem
except ImportError:
    # PyQt5 compatibility
    pass
