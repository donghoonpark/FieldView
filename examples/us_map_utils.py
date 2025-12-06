import os
import re
import json
import numpy as np
import xml.etree.ElementTree as ET
from qtpy.QtGui import QPainterPath, QPolygonF, QPainterPathStroker
from qtpy.QtCore import Qt
from typing import Dict, Tuple, List


def parse_svg_path_to_qpainterpath(d_str: str) -> QPainterPath:
    """Parses a simple SVG path string (M, L, C, Z) into a QPainterPath."""
    path = QPainterPath()

    # Regex to tokenize commands and numbers
    tokens = re.findall(r"([a-zA-Z])|([-+]?\d*\.?\d+)", d_str)

    current_cmd = None
    args: List[float] = []

    def flush_command():
        nonlocal current_cmd, args
        if current_cmd == "M":
            for i in range(0, len(args), 2):
                path.moveTo(args[i], args[i + 1])
        elif current_cmd == "L":
            for i in range(0, len(args), 2):
                path.lineTo(args[i], args[i + 1])
        elif current_cmd == "C":
            for i in range(0, len(args), 6):
                path.cubicTo(
                    args[i],
                    args[i + 1],
                    args[i + 2],
                    args[i + 3],
                    args[i + 4],
                    args[i + 5],
                )
        elif current_cmd == "Z":
            path.closeSubpath()
        elif current_cmd == "z":
            path.closeSubpath()

        args = []

    for cmd, num in tokens:
        if cmd:
            if current_cmd:
                flush_command()
            current_cmd = cmd
        else:
            args.append(float(num))

    if current_cmd:
        flush_command()

    return path


def get_state_data(svg_path: str) -> Tuple[Dict[str, QPainterPath], Dict[str, Tuple[float, float]]]:
    """Parses the US map SVG to get state paths and centroids."""
    if not os.path.exists(svg_path):
        print(f"Error: {svg_path} not found")
        return {}, {}

    tree = ET.parse(svg_path)
    root = tree.getroot()

    state_paths: Dict[str, QPainterPath] = {}
    centroids: Dict[str, Tuple[float, float]] = {}

    # Helper to process a path element
    def process_path(element, state_id):
        d = element.get("d")
        if d:
            qpath = parse_svg_path_to_qpainterpath(d)
            if state_id in state_paths:
                state_paths[state_id].addPath(qpath)
            else:
                state_paths[state_id] = qpath

            # Update centroid (simplified: average of bounding rect center)
            rect = qpath.boundingRect()
            centroids[state_id] = (rect.center().x(), rect.center().y())

    # Iterate over all paths and groups
    # Direct paths
    for path in root.findall(".//{http://www.w3.org/2000/svg}path"):
        state_id = path.get("id")
        if state_id and len(state_id) == 2:  # Simple check for state codes
            process_path(path, state_id)

    # Groups (like MI, with multiple islands/peninsulas)
    for g in root.findall(".//{http://www.w3.org/2000/svg}g"):
        state_id = g.get("id")
        if state_id and len(state_id) == 2:
            for path in g.findall(".//{http://www.w3.org/2000/svg}path"):
                process_path(path, state_id)

    return state_paths, centroids


def get_us_boundary(state_paths: Dict[str, QPainterPath]) -> QPainterPath:
    """Creates a simplified, merged US boundary path from state paths."""
    us_boundary = QPainterPath()
    for qpath in state_paths.values():
        us_boundary.addPath(qpath)

    # 0. Merge all state paths into a single outline to remove internal borders/gaps
    stroker = QPainterPathStroker()
    stroker.setWidth(1.0)  # Small overlap to seal cracks
    stroker.setJoinStyle(Qt.RoundJoin)
    stroker.setCapStyle(Qt.RoundCap)

    stroke_path = stroker.createStroke(us_boundary)
    us_boundary = us_boundary.united(stroke_path)
    us_boundary = us_boundary.simplified()

    # 1. Convert to subpath polygons to handle islands
    sub_polygons = us_boundary.toSubpathPolygons()

    # 2. Filter out small islands (e.g., < 500 sq pixels)
    min_area = 500.0
    kept_polygons = []

    for poly in sub_polygons:
        brect = poly.boundingRect()
        area = brect.width() * brect.height()

        if area > min_area:
            kept_polygons.append(poly)

    # 3. Simplify and Reconstruct
    final_boundary = QPainterPath()

    for poly in kept_polygons:
        simplified_points = []
        if poly.count() > 0:
            last_pt = poly.at(0)
            simplified_points.append(last_pt)
            min_dist_sq = 5.0 * 5.0  # 5 pixel minimum distance

            for i in range(1, poly.count()):
                pt = poly.at(i)
                dx = pt.x() - last_pt.x()
                dy = pt.y() - last_pt.y()
                if (dx * dx + dy * dy) > min_dist_sq:
                    simplified_points.append(pt)
                    last_pt = pt

            # Close the loop if needed
            if len(simplified_points) > 2:
                d_start = (
                    simplified_points[-1].x() - simplified_points[0].x()
                ) ** 2 + (simplified_points[-1].y() - simplified_points[0].y()) ** 2
                if d_start > min_dist_sq:
                    simplified_points.append(simplified_points[0])

        if len(simplified_points) >= 3:
            final_boundary.addPolygon(QPolygonF(simplified_points))

    return final_boundary


def load_weather_data() -> Dict[str, float]:
    """Loads weather data from JSON file."""
    weather_data_path = os.path.join(os.path.dirname(__file__), "us_weather_data.json")
    real_weather_data = {}
    if os.path.exists(weather_data_path):
        try:
            with open(weather_data_path, "r") as f:
                real_weather_data = json.load(f)
            print(f"Loaded real weather data for {len(real_weather_data)} states.")
        except Exception as e:
            print(f"Failed to load weather data: {e}")
    return real_weather_data


def generate_us_dataset(centroids: Dict[str, Tuple[float, float]], weather_data: Dict[str, float]) -> Tuple[np.ndarray, np.ndarray]:
    """Generates points and values arrays for the US map."""
    points = []
    values = []

    for state_id, centroid in centroids.items():
        # Exclude Alaska and Hawaii from the main map
        if state_id in ["AK", "HI"]:
            continue

        points.append([centroid[0], centroid[1]])

        # Use real data if available, otherwise random
        if state_id in weather_data:
            val = weather_data[state_id]
        else:
            # Fallback for missing states
            normalized_y = centroid[1] / 600.0
            val = 30.0 * normalized_y - 5.0 + np.random.uniform(-5, 5)

        values.append(val)

    return np.array(points), np.array(values)
