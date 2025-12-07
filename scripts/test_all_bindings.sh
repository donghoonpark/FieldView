#!/bin/bash
set -e

echo "========================================"
echo "Running tests with PySide6..."
echo "========================================"
QT_API=pyside6 uv run --with pyside6 pytest

echo ""
echo "========================================"
echo "Running tests with PyQt6..."
echo "========================================"
QT_API=pyqt6 uv run --with pyqt6 pytest

echo ""
echo "========================================"
echo "Running tests with PyQt5..."
echo "========================================"
QT_API=pyqt5 uv run --with pyqt5 pytest

echo ""
echo "All tests passed for all bindings!"
