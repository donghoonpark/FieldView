import numpy as np
from fieldview.utils.interpolation import FastRBFInterpolator, BoundaryPointGenerator


class InterpolatorCache:
    """
    Manages cached interpolators to avoid re-fitting when geometry hasn't changed.
    Supports LRU-style eviction to keep memory usage in check.
    """

    def __init__(self, max_size=5):
        self._cache = {}  # Key: cache tuple, Value: (FastRBFInterpolator, BoundaryPointGenerator)
        self._access_order = []  # List of keys, most recent last
        self._max_size = max_size

    def _hash_boundary_shape(self, boundary_shape):
        if boundary_shape.isEmpty():
            return 0

        return hash(
            tuple(
                (boundary_shape.at(i).x(), boundary_shape.at(i).y())
                for i in range(boundary_shape.count())
            )
        )

    def get_interpolator(
        self,
        grid_size,
        points,
        boundary_shape,
        neighbors=30,
        kernel="thin_plate_spline",
    ):
        """
        Returns a fitted FastRBFInterpolator.
        If a matching interpolator exists in cache, returns it.
        Otherwise, fits a new one and caches it.
        """
        # 1. Generate Cache Key
        points_hash = hash(points.tobytes())
        boundary_hash = self._hash_boundary_shape(boundary_shape)

        key = (grid_size, points_hash, boundary_hash, neighbors, kernel)

        # 2. Check Cache
        if key in self._cache:
            # Move to end (most recently used)
            self._access_order.remove(key)
            self._access_order.append(key)
            return self._cache[key]

        # 3. Fit New Interpolator
        boundary_gen = BoundaryPointGenerator()
        boundary_gen.fit(points, boundary_shape)
        boundary_points = boundary_gen.get_boundary_points()

        if len(boundary_points) > 0:
            all_source_points = np.vstack((points, boundary_points))
        else:
            all_source_points = points

        # Create Grid
        rect = boundary_shape.boundingRect()
        dx = rect.width() / grid_size
        dy = rect.height() / grid_size
        # Expand by 1 pixel
        expanded_rect = rect.adjusted(-dx, -dy, dx, dy)
        expanded_grid_size = grid_size + 2

        x = np.linspace(expanded_rect.left(), expanded_rect.right(), expanded_grid_size)
        y = np.linspace(expanded_rect.top(), expanded_rect.bottom(), expanded_grid_size)
        X, Y = np.meshgrid(x, y)
        grid_points = np.column_stack((X.ravel(), Y.ravel()))

        # Fit RBF
        rbf = FastRBFInterpolator(neighbors=neighbors, kernel=kernel)
        rbf.fit(all_source_points, grid_points)

        # 4. Update Cache
        if len(self._cache) >= self._max_size:
            # Evict oldest
            oldest_key = self._access_order.pop(0)
            del self._cache[oldest_key]

        self._cache[key] = (rbf, boundary_gen)
        self._access_order.append(key)

        return self._cache[key]
