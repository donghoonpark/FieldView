import numpy as np
from qtpy.QtGui import QPolygonF
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtCore import QRectF
else:
    from qtpy.QtCore import QRectF
from fieldview.utils.grid_manager import InterpolatorCache


def test_interpolator_cache_caching():
    cache = InterpolatorCache(max_size=2)

    # Setup dummy data
    # Setup dummy data - Use enough points to avoid singular matrix with TPS
    rng = np.random.default_rng(42)
    points = rng.random((10, 2)) * 10
    boundary = QPolygonF(QRectF(0, 0, 10, 10))
    grid_size = 10

    # 1. First Get - Should fit new
    interp1, _ = cache.get_interpolator(grid_size, points, boundary)
    assert interp1._is_fitted

    # 2. Second Get (Same args) - Should return same instance
    interp2, _ = cache.get_interpolator(grid_size, points, boundary)
    assert interp1 is interp2

    # 3. Change Grid Size - Should return new instance
    interp3, _ = cache.get_interpolator(20, points, boundary)
    assert interp3 is not interp1

    # 4. Change Points - Should return new instance
    points2 = rng.random((10, 2)) * 10
    interp4, _ = cache.get_interpolator(grid_size, points2, boundary)
    assert interp4 is not interp1


def test_interpolator_cache_eviction():
    cache = InterpolatorCache(max_size=2)

    rng = np.random.default_rng(42)
    points = rng.random((10, 2)) * 10
    boundary = QPolygonF(QRectF(0, 0, 10, 10))

    # Fill cache
    i1, _ = cache.get_interpolator(10, points, boundary)  # Cache: [10]
    i2, _ = cache.get_interpolator(20, points, boundary)  # Cache: [10, 20]

    # Access 10 again to make it recent
    cache.get_interpolator(10, points, boundary)  # Cache: [20, 10]

    # Add new one, should evict 20 (LRU)
    i3, _ = cache.get_interpolator(30, points, boundary)  # Cache: [10, 30]

    # Check if 20 is gone (by checking internal cache, though implementation detail)
    # Or by checking if getting 20 returns a NEW instance
    i2_new, _ = cache.get_interpolator(20, points, boundary)
    assert i2_new is not i2


if __name__ == "__main__":
    test_interpolator_cache_caching()
    test_interpolator_cache_eviction()
    print("All tests passed!")
