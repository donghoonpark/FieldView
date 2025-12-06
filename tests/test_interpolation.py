import numpy as np
from scipy.interpolate import RBFInterpolator
from fieldview.utils.interpolation import FastRBFInterpolator


def test_fast_rbf_correctness():
    # 1. Setup Data
    # Random source points
    rng = np.random.default_rng(42)
    source_points = rng.random((20, 2)) * 100
    values = rng.random(20) * 10

    # Grid points
    x = np.linspace(0, 100, 10)
    y = np.linspace(0, 100, 10)
    X, Y = np.meshgrid(x, y)
    grid_points = np.column_stack((X.ravel(), Y.ravel()))

    # 2. Scipy RBF
    scipy_rbf = RBFInterpolator(
        source_points, values, neighbors=10, kernel="thin_plate_spline"
    )
    scipy_result = scipy_rbf(grid_points)

    # 3. Fast RBF
    fast_rbf = FastRBFInterpolator(neighbors=10, kernel="thin_plate_spline")
    fast_rbf.fit(source_points, grid_points)
    fast_result = fast_rbf.predict(values)

    # 4. Compare
    # Should be very close, allowing for small float errors
    assert fast_result is not None
    np.testing.assert_allclose(fast_result, scipy_result, rtol=1e-5, atol=1e-5)


def test_fast_rbf_caching_speed():
    # 1. Setup Data
    rng = np.random.default_rng(42)
    source_points = rng.random((50, 2)) * 100
    grid_points = rng.random((1000, 2)) * 100

    fast_rbf = FastRBFInterpolator(neighbors=20)
    fast_rbf.fit(source_points, grid_points)

    # 2. Measure Prediction Time
    import time

    start = time.perf_counter()
    for _ in range(100):
        values = rng.random(50)
        _ = fast_rbf.predict(values)
    duration = time.perf_counter() - start

    # Just ensure it runs reasonably fast (not a strict assertion, but sanity check)
    print(f"100 predictions took {duration:.4f}s")
    assert duration < 1.0  # Should be very fast


if __name__ == "__main__":
    test_fast_rbf_correctness()
    test_fast_rbf_caching_speed()
    print("All tests passed!")
