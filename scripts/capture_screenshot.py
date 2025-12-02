import sys
import os
import time

# Set offscreen platform before importing PySide6
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QTimer, QSize, QRectF
from PySide6.QtGui import QImage, QPainter, QColor

# Add project root to path to import examples
# Even though quick_start handles imports, we need to import quick_start itself
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from examples import quick_start

def capture():
    print("Starting application (headless)...")
    app, view = quick_start.run()
    
    # Ensure assets directory exists
    assets_dir = os.path.join(os.path.dirname(__file__), '..', 'assets')
    os.makedirs(assets_dir, exist_ok=True)
    output_path = os.path.join(assets_dir, 'quick_start.png')

    def take_screenshot():
        print("Rendering scene...")
        
        # Create an image to render into
        image = QImage(600, 450, QImage.Format.Format_ARGB32)
        image.fill(QColor(30, 30, 30)) # Dark background
        
        painter = QPainter(image)
        scene = view.scene()
        
        # Render the scene
        # We use the scene rect which was set in quick_start.py
        scene.render(painter, target=QRectF(0, 0, 600, 450), source=scene.sceneRect())
        
        painter.end()
        
        # Save
        image.save(output_path)
        print(f"Screenshot saved to {output_path}")
        
        app.quit()

    # Wait a bit for rendering to finish
    QTimer.singleShot(1000, take_screenshot)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    capture()
