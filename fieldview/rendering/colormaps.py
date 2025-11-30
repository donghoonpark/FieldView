from PySide6.QtGui import QColor
import numpy as np

class Colormap:
    """
    Simple colormap implementation using linear interpolation of stops.
    """
    def __init__(self, name, stops):
        """
        Args:
            name (str): Name of the colormap.
            stops (list): List of (position, color_hex) tuples. 
                          Position is 0.0 to 1.0.
        """
        self.name = name
        self.stops = sorted(stops, key=lambda x: x[0])
        
    def map(self, value):
        """
        Maps a value (0.0 to 1.0) to a QColor.
        """
        value = max(0.0, min(1.0, value))
        
        # Find segment
        for i in range(len(self.stops) - 1):
            p1, c1_hex = self.stops[i]
            p2, c2_hex = self.stops[i+1]
            
            if p1 <= value <= p2:
                t = (value - p1) / (p2 - p1) if p2 > p1 else 0
                c1 = QColor(c1_hex)
                c2 = QColor(c2_hex)
                
                r = int(c1.red() * (1-t) + c2.red() * t)
                g = int(c1.green() * (1-t) + c2.green() * t)
                b = int(c1.blue() * (1-t) + c2.blue() * t)
                
                return QColor(r, g, b)
                
        # Fallback (should cover 0.0 to 1.0 if stops are correct)
        return QColor(self.stops[-1][1])

    def get_lut(self, size=256):
        """
        Returns a numpy array of shape (size,) containing uint32 ARGB values.
        """
        if hasattr(self, '_lut') and len(self._lut) == size:
            return self._lut
            
        lut = np.zeros(size, dtype=np.uint32)
        
        for i in range(size):
            val = i / (size - 1)
            color = self.map(val)
            # ARGB32 format: 0xAARRGGBB
            # QColor.rgba() returns 0xAARRGGBB (unsigned int)
            lut[i] = color.rgba()
            
        self._lut = lut
        return lut

# Standard Colormaps (Approximations)
VIRIDIS = Colormap("viridis", [
    (0.0, "#440154"), (0.25, "#3b528b"), (0.5, "#21918c"), (0.75, "#5ec962"), (1.0, "#fde725")
])

PLASMA = Colormap("plasma", [
    (0.0, "#0d0887"), (0.25, "#7e03a8"), (0.5, "#cc4778"), (0.75, "#f89540"), (1.0, "#f0f921")
])

INFERNO = Colormap("inferno", [
    (0.0, "#000004"), (0.25, "#57106e"), (0.5, "#bb3754"), (0.75, "#f98e09"), (1.0, "#fcffa4")
])

MAGMA = Colormap("magma", [
    (0.0, "#000004"), (0.25, "#51127c"), (0.5, "#b73779"), (0.75, "#fc8961"), (1.0, "#fcfdbf")
])

COOLWARM = Colormap("coolwarm", [
    (0.0, "#3b4cc0"), (0.5, "#dddddd"), (1.0, "#b40426")
])

JET = Colormap("jet", [
    (0.0, "#000080"), (0.125, "#0000ff"), (0.375, "#00ffff"), (0.625, "#ffff00"), (0.875, "#ff0000"), (1.0, "#800000")
])

COLORMAPS = {
    "viridis": VIRIDIS,
    "plasma": PLASMA,
    "inferno": INFERNO,
    "magma": MAGMA,
    "coolwarm": COOLWARM,
    "jet": JET
}

def get_colormap(name):
    return COLORMAPS.get(name.lower(), VIRIDIS)
