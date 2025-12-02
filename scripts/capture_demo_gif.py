"""Generate an animated demo of the FieldView widget.

This script spins up the demo application offscreen, walks through a few
interactive features, and stitches the frames into a GIF. It reuses the live
widgets so the animation reflects actual runtime behavior.
"""

import argparse
import base64
import os
import sys
from dataclasses import dataclass
from typing import Callable, Iterable, List, Tuple

# Ensure offscreen rendering before importing Qt
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import imageio.v3 as iio
import numpy as np
from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

# Allow importing the demo module
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from examples.demo import DemoApp  # noqa: E402


@dataclass
class CaptionedStep:
    caption: str
    action: Callable[[], None] | None = None
    delay_ms: int | None = None


def _qimage_to_numpy(image: QImage) -> np.ndarray:
    """Convert a QImage to an RGBA numpy array suitable for imageio."""
    formatted = image.convertToFormat(QImage.Format.Format_RGBA8888)
    width, height = formatted.width(), formatted.height()
    buffer = formatted.bits().tobytes()
    return np.frombuffer(buffer, np.uint8).reshape((height, width, 4)).copy()


def _render_frame(window: DemoApp, size: QSize, caption: str | None) -> np.ndarray:
    """Render the full demo window into an array with an optional caption."""
    snapshot = window.grab()
    image = snapshot.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    image = image.scaled(size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

    painter = QPainter(image)
    if caption:
        painter.setPen(QColor("white"))
        painter.fillRect(10, 10, 480, 38, QColor(0, 0, 0, 180))
        painter.drawText(QRectF(16, 10, 460, 38), caption)
    painter.end()

    return _qimage_to_numpy(image)


def _default_steps(window: DemoApp) -> List[CaptionedStep]:
    """Predefined walkthrough showcasing the main interactions."""

    app = QApplication.instance()

    def circular_boundary() -> None:
        window.change_boundary_shape("Circle")

    def custom_polygon() -> None:
        window.change_boundary_shape("Custom Polygon")

    def enable_editing() -> None:
        window.toggle_polygon_handles(True)

    def add_and_drag_vertex() -> None:
        insert_after = 1
        start_pos = QPointF(-40, 260)
        window.on_polygon_point_added(insert_after, start_pos)
        if app:
            app.processEvents()
        QTest.qWait(1000)

        new_index = insert_after + 1
        window.on_handle_moved(new_index, QPointF(140, 240))
        if app:
            app.processEvents()
        QTest.qWait(1000)

    def hide_values() -> None:
        window.value_layer.setVisible(False)

    def show_labels() -> None:
        window.label_layer.setVisible(True)

    def change_colormap() -> None:
        setattr(window.heatmap_layer, "colormap", "plasma")

    def start_noise() -> None:
        window.btn_sim.setChecked(True)

    return [
        CaptionedStep("Initial view", None, 1000),
        CaptionedStep("Switch to circular boundary", circular_boundary, 1000),
        CaptionedStep("Back to custom polygon", custom_polygon, 1000),
        CaptionedStep("Enable polygon editing", enable_editing, 1000),
        CaptionedStep("Add and drag a new vertex", add_and_drag_vertex, 0),
        CaptionedStep("Hide value overlays", hide_values, 1000),
        CaptionedStep("Show label overlays", show_labels, 1000),
        CaptionedStep("Change colormap", change_colormap, 1000),
        CaptionedStep("Start noise simulator", start_noise, 3000),
    ]


def generate_demo_gif(
    output_path: str | None = None,
    *,
    size: QSize | None = None,
    steps_builder: Callable[[DemoApp], Iterable[CaptionedStep]] | None = None,
    base64_path: str | None = None,
    step_delay_ms: int = 1000,
    linger_frames: int = 2,
) -> str:
    """Create a GIF that exercises the demo widget.

    Args:
        output_path: Where to store the GIF. Defaults to ``assets/demo.gif``.
        size: Image size to render; defaults to 800x680 to keep the demo width fixed.
        steps_builder: Optional factory that receives the live ``DemoApp``
            instance and returns an iterable of ``(caption, action)`` pairs.
        base64_path: Optional path to also emit a Base64-encoded version of the
            GIF for environments that block binary uploads.

    Returns:
        The absolute path to the generated GIF.
    """

    app = QApplication.instance() or QApplication(sys.argv)
    window = DemoApp()
    render_size = size or QSize(800, 680)
    window.resize(render_size)
    window.show()
    steps = list(steps_builder(window) if steps_builder else _default_steps(window))

    frames: List[np.ndarray] = []
    for step in steps:
        if isinstance(step, tuple):
            step = CaptionedStep(*step)

        if step.action:
            step.action()
        app.processEvents()
        delay = step.delay_ms if step.delay_ms is not None else step_delay_ms
        if delay > 0:
            QTest.qWait(delay)
        frame = _render_frame(window, render_size, step.caption)
        frames.extend([frame] * max(1, linger_frames))

    assets_dir = os.path.join(PROJECT_ROOT, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    output_path = output_path or os.path.join(assets_dir, "demo.gif")

    iio.imwrite(output_path, frames, format="GIF", duration=0.85, loop=0)

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
    parser.add_argument(
        "--step-delay-ms",
        type=int,
        default=1000,
        help="How long to pause after each step so changes are visible",
    )
    parser.add_argument(
        "--linger-frames",
        type=int,
        default=2,
        help="How many repeated frames to emit per step to slow playback",
    )
    args = parser.parse_args()

    path = generate_demo_gif(
        output_path=args.output_path,
        base64_path=args.base64_path,
        step_delay_ms=args.step_delay_ms,
        linger_frames=args.linger_frames,
    )

    print(f"Demo GIF saved to: {path}")
    if args.base64_path:
        print(f"Base64 version saved to: {os.path.abspath(args.base64_path)}")


if __name__ == "__main__":
    main()
