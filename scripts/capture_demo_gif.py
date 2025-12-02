"""Generate an animated demo of the FieldView widget.

This script spins up the demo application offscreen, walks through a few
interactive features, and stitches the frames into a GIF. It reuses the live
widgets so the animation reflects actual runtime behavior.
"""

import argparse
import base64
import os
import sys
from typing import Callable, Iterable, List, Tuple

# Ensure offscreen rendering before importing Qt
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import imageio.v3 as iio
import numpy as np
from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

# Allow importing the demo module
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from examples.demo import DemoApp  # noqa: E402

CaptionedStep = Tuple[str, Callable[[], None] | None]


def _qimage_to_numpy(image: QImage) -> np.ndarray:
    """Convert a QImage to an RGBA numpy array suitable for imageio."""
    formatted = image.convertToFormat(QImage.Format.Format_RGBA8888)
    width, height = formatted.width(), formatted.height()
    buffer = formatted.bits().tobytes()
    return np.frombuffer(buffer, np.uint8).reshape((height, width, 4)).copy()


def _render_frame(window: DemoApp, size: QSize, caption: str | None) -> np.ndarray:
    """Render the demo scene into an array with an optional caption overlay."""
    scene = window.scene
    scene.setSceneRect(scene.itemsBoundingRect())

    window.view.fitInView(scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    image = QImage(size, QImage.Format.Format_ARGB32)
    image.fill(QColor(30, 30, 30))

    painter = QPainter(image)
    scene.render(painter, target=QRectF(0, 0, size.width(), size.height()), source=scene.sceneRect())

    if caption:
        painter.setPen(QColor("white"))
        painter.fillRect(10, 10, 420, 34, QColor(0, 0, 0, 180))
        painter.drawText(QRectF(16, 10, 400, 34), caption)

    painter.end()
    return _qimage_to_numpy(image)


def _default_steps(window: DemoApp) -> List[CaptionedStep]:
    """Predefined set of actions to showcase key features."""

    def enable_labels() -> None:
        window.label_layer.setVisible(True)

    def warm_colormap() -> None:
        setattr(window.heatmap_layer, "colormap", "magma")

    def offset_floorplan() -> None:
        window.set_svg_origin(60.0, -40.0)

    def circular_boundary() -> None:
        window.change_boundary_shape("Circle")

    def jitter_values() -> None:
        window.spin_noise.setValue(15.0)
        window.apply_noise()

    return [
        ("Initial view", None),
        ("Labels enabled", enable_labels),
        ("Warm colormap", warm_colormap),
        ("Offset floorplan origin", offset_floorplan),
        ("Circular boundary", circular_boundary),
        ("Jittered values", jitter_values),
    ]


def generate_demo_gif(
    output_path: str | None = None,
    *,
    size: QSize | None = None,
    steps_builder: Callable[[DemoApp], Iterable[CaptionedStep]] | None = None,
    base64_path: str | None = None,
) -> str:
    """Create a GIF that exercises the demo widget.

    Args:
        output_path: Where to store the GIF. Defaults to ``assets/demo.gif``.
        size: Image size to render; defaults to 900x700.
        steps_builder: Optional factory that receives the live ``DemoApp``
            instance and returns an iterable of ``(caption, action)`` pairs.
        base64_path: Optional path to also emit a Base64-encoded version of the
            GIF for environments that block binary uploads.

    Returns:
        The absolute path to the generated GIF.
    """

    app = QApplication.instance() or QApplication(sys.argv)
    window = DemoApp()
    window.show()

    render_size = size or QSize(900, 700)
    steps = list(steps_builder(window) if steps_builder else _default_steps(window))

    frames: List[np.ndarray] = []
    for caption, action in steps:
        if action:
            action()
        app.processEvents()
        frames.append(_render_frame(window, render_size, caption))

    assets_dir = os.path.join(PROJECT_ROOT, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    output_path = output_path or os.path.join(assets_dir, "demo.gif")

    iio.imwrite(output_path, frames, format="GIF", duration=0.8, loop=0)

    if base64_path:
        with open(output_path, "rb") as fp:
            encoded = base64.b64encode(fp.read()).decode("ascii")
        with open(base64_path, "w", encoding="utf-8") as fp:
            fp.write(encoded)

    window.close()
    app.quit()

    return os.path.abspath(output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", dest="output_path", help="Where to store the rendered GIF"
    )
    parser.add_argument(
        "--base64",
        dest="base64_path",
        help="Optional path for a Base64-encoded copy of the GIF",
    )
    args = parser.parse_args()

    path = generate_demo_gif(output_path=args.output_path, base64_path=args.base64_path)

    print(f"Demo GIF saved to: {path}")
    if args.base64_path:
        print(f"Base64 version saved to: {os.path.abspath(args.base64_path)}")


if __name__ == "__main__":
    main()
