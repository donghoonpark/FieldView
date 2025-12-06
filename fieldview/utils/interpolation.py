import numpy as np
from scipy.interpolate import RBFInterpolator
from scipy.spatial import cKDTree
from typing import Optional, Literal

KernelType = Literal[
    "thin_plate_spline",
    "linear",
    "cubic",
    "quintic",
    "gaussian",
    "multiquadric",
    "inverse_multiquadric",
]


class BoundaryPointGenerator:
    """
    Generates boundary points and computes their values using IDW.
    Pre-computes weights for fast updates.
    """

    def __init__(self):
        self._boundary_points = None
        self._idw_indices = None
        self._idw_weights = None
        self._is_fitted = False

    def fit(
        self,
        points: np.ndarray,
        boundary_shape,
        target_segment_length: Optional[float] = None,
    ):
        """
        Generates boundary points and computes IDW weights.
        """
        if len(points) < 2:
            self._is_fitted = False
            return

        # 1. Generate Boundary Points
        self._boundary_points = self._generate_points(
            points, boundary_shape, target_segment_length
        )

        if len(self._boundary_points) == 0:
            self._is_fitted = False
            return

        # 2. Compute IDW Weights
        tree = cKDTree(points)
        dists, indices = tree.query(self._boundary_points, k=2)

        # Avoid division by zero
        dists = np.maximum(dists, 1e-9)
        weights = 1.0 / dists

        # Normalize weights
        row_sums = weights.sum(axis=1)[:, np.newaxis]
        self._idw_weights = weights / row_sums
        self._idw_indices = indices

        self._is_fitted = True

    def transform(self, values: np.ndarray) -> np.ndarray:
        """
        Computes values for boundary points using pre-computed weights.
        """
        if not self._is_fitted:
            return np.empty((0,))

        # Get values of nearest neighbors
        # values[indices] shape: (n_boundary, 2)
        neighbor_values = values[self._idw_indices]

        # Weighted sum: sum(weights * values, axis=1)
        # weights shape: (n_boundary, 2)
        boundary_values = np.sum(self._idw_weights * neighbor_values, axis=1)

        return boundary_values

    def get_boundary_points(self) -> np.ndarray:
        if not self._is_fitted or self._boundary_points is None:
            return np.empty((0, 2))
        return self._boundary_points

    def _generate_points(
        self,
        points: np.ndarray,
        boundary_shape,
        target_segment_length: Optional[float] = None,
    ) -> np.ndarray:
        # Adaptive Sampling
        if target_segment_length is None:
            tree = cKDTree(points)
            distances, _ = tree.query(points, k=2)
            avg_dist = np.mean(distances[:, 1])
            target_segment_length = avg_dist * 1.2
            if target_segment_length <= 0:
                target_segment_length = 10.0

        boundary_points_list = []

        # Iterate through polygon edges
        poly_points = [boundary_shape.at(i) for i in range(boundary_shape.count())]
        if boundary_shape.isClosed():
            if poly_points[0] != poly_points[-1]:
                poly_points.append(poly_points[0])
        else:
            poly_points.append(poly_points[0])  # Close the loop

        for i in range(len(poly_points) - 1):
            p1 = np.array([poly_points[i].x(), poly_points[i].y()])
            p2 = np.array([poly_points[i + 1].x(), poly_points[i + 1].y()])

            segment_len = np.linalg.norm(p2 - p1)
            n_segments = int(np.ceil(segment_len / target_segment_length))
            n_segments = max(1, n_segments)

            for j in range(n_segments):
                t = j / n_segments
                pt = p1 + t * (p2 - p1)
                boundary_points_list.append(pt)

        # Filter points
        # 1. Remove duplicates and close points within boundary points
        # 2. Remove points too close to existing data points

        if not boundary_points_list:
            return np.empty((0, 2))

        boundary_points = np.array(boundary_points_list)

        # 1. Filter boundary points against themselves
        # We want to keep points that are at least 'min_spacing' apart
        # Increased to 15.0 to prevent high density of boundary points from dominating
        # the local neighborhood (especially with low 'neighbors' count), which causes
        # TPS artifacts/overfitting around isolated data points like FL.
        min_spacing = 15.0

        # Sort by x coordinate to make the filtering somewhat deterministic/efficient
        # or just use a simple greedy approach

        if len(boundary_points) > 0:
            # Use cKDTree for efficient radius search
            # But we need a greedy selection.
            # Simple approach: Iterate and skip if close to already kept
            # For speed, we can use a simple grid or just brute force if N is small (<2000)
            # Or use cKDTree.query_ball_point on the *kept* points.

            # Let's use a simple mask approach with cKDTree
            # This is iterative and might be slow for huge N, but N is ~1000.

            # Faster approach: `scipy.spatial.KDTree` doesn't support "select subset with min dist" directly.
            # We can use `query_pairs` to find all pairs < r, then remove one of them.

            tree = cKDTree(boundary_points)
            pairs = tree.query_pairs(r=min_spacing)

            drop_indices = set()
            for i, j in pairs:
                if i in drop_indices or j in drop_indices:
                    continue
                # Drop the one with higher index (arbitrary)
                drop_indices.add(j)

            mask = np.ones(len(boundary_points), dtype=bool)
            mask[list(drop_indices)] = False
            boundary_points = boundary_points[mask]

        # 2. Remove points close to data points
        if len(points) > 0:
            tree = cKDTree(points)
            # Find boundary points that are within a small radius of any data point
            radius = 5.0  # Increased from 1.0 to 5.0
            indices_to_remove = tree.query_ball_point(boundary_points, radius)

            # indices_to_remove is a list of lists of neighbors
            mask = np.array([len(x) == 0 for x in indices_to_remove], dtype=bool)
            boundary_points = boundary_points[mask]

        return boundary_points


class FastRBFInterpolator:
    """
    RBF Interpolator that pre-computes the interpolation matrix.
    Prediction is a simple matrix multiplication: Z = L @ values
    """

    def __init__(self, neighbors: int = 30, kernel: KernelType = "thin_plate_spline"):
        self.neighbors = neighbors
        self.kernel = kernel
        self._matrix = None
        self._is_fitted = False

    def fit(self, source_points: np.ndarray, grid_points: np.ndarray):
        """
        Computes the linear operator matrix L.
        """
        if len(source_points) == 0 or len(grid_points) == 0:
            self._is_fitted = False
            return

        # We want to find a matrix L such that Z = L @ V
        # RBFInterpolator(y) internally solves A @ w = y, then predicts Z = B @ w
        # So Z = B @ (A^-1 @ y) = (B @ A^-1) @ y
        # L = B @ A^-1

        # However, scipy's RBFInterpolator doesn't expose A^-1 directly easily for all kernels/modes.
        # But we can compute L by passing the identity matrix as 'y'.
        # If y = I (identity), then the output is exactly column j corresponds to the response to a unit impulse at source j.
        # This is exactly the matrix L.

        n_source = len(source_points)

        # Create identity matrix as values
        # Shape: (n_source, n_source)
        identity = np.eye(n_source)

        try:
            # Fit RBF with identity matrix
            # Neighbors logic is handled by scipy
            interp = RBFInterpolator(
                source_points, identity, neighbors=self.neighbors, kernel=self.kernel
            )

            # Predict on grid points
            # Output shape: (n_grid, n_source)
            self._matrix = interp(grid_points)
            self._is_fitted = True

        except Exception as e:
            print(f"FastRBF fit failed: {e}")
            self._is_fitted = False

    def predict(self, values: np.ndarray) -> Optional[np.ndarray]:
        """
        Predicts values on the grid.
        values shape: (n_source,)
        Returns shape: (n_grid,)
        """
        if not self._is_fitted:
            return None

        # Z = L @ values
        # (n_grid, n_source) @ (n_source,) -> (n_grid,)
        return self._matrix @ values
