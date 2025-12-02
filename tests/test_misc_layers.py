import base64
import os

import pytest
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtCore import QByteArray, QPointF, QRectF, QSize

from fieldview.core.data_container import DataContainer
from fieldview.layers.pin_layer import PinLayer
from fieldview.layers.svg_layer import SvgLayer
from examples import quick_start
from scripts.capture_demo_gif import generate_demo_gif

def test_svg_layer(qtbot, tmp_path):
    layer = SvgLayer()

    # Create a dummy SVG file
    svg_content = b'<svg width="100" height="100"><circle cx="50" cy="50" r="40" stroke="green" stroke-width="4" fill="yellow" /></svg>'
    svg_file = tmp_path / "test.svg"
    svg_file.write_bytes(svg_content)

    layer.load_svg(str(svg_file))
    assert layer._renderer.isValid()

    # Default origin should match viewbox
    assert layer.boundingRect() == QRectF(0, 0, 100, 100)

    # Manual origin repositions bounding rect
    layer.set_origin(QPointF(10, -20))
    assert layer.boundingRect() == QRectF(10, -20, 100, 100)

def test_pin_layer(qtbot):
    dc = DataContainer()
    dc.set_data([[0, 0]], [10])
    layer = PinLayer(dc)
    
    # Create a dummy pixmap
    pixmap = QPixmap(10, 10)
    layer.set_icon(pixmap)

    assert layer.icon == pixmap


def test_quick_start_screenshot(tmp_path, qtbot):
    # Ensure headless rendering
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    app, view = quick_start.run()

    image = QImage(600, 600, QImage.Format.Format_ARGB32)
    image.fill(0)

    painter = QPainter(image)
    scene = view.scene()
    scene.render(painter, target=QRectF(0, 0, 600, 600), source=scene.sceneRect())
    painter.end()

    output_path = tmp_path / "quick_start.png"
    assert image.save(str(output_path))
    assert output_path.exists()


def test_demo_gif_generation(tmp_path, qtbot):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    def minimal_steps(window):
        return [
            ("Initial view", None),
            ("Noise applied", window.apply_noise),
        ]

    output = tmp_path / "demo.gif"
    base64_output = tmp_path / "demo.gif.b64"
    path = generate_demo_gif(
        str(output),
        size=QSize(360, 280),
        steps_builder=minimal_steps,
        base64_path=str(base64_output),
        step_delay_ms=0,
        linger_frames=1,
    )

    assert os.path.exists(path)
    assert os.path.getsize(path) > 0
    assert base64_output.exists()
    decoded = base64.b64decode(base64_output.read_text())
    assert decoded.startswith(b"GIF89a")
    assert decoded == output.read_bytes()
