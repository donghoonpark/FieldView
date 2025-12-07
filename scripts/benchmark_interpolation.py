import time
import numpy as np
from scipy.interpolate import RBFInterpolator
from fieldview.utils.interpolation import FastRBFInterpolator
import platform
import json


def benchmark():
    print("Benchmarking Interpolation Performance")
    print(f"Python: {platform.python_version()}")
    print(f"NumPy: {np.__version__}")

    # Setup data
    n_points = 100
    n_grid = 200  # 100x100 = 40,000 query points

    rng = np.random.default_rng(42)
    points = rng.random((n_points, 2)) * 100
    values = np.sin(points[:, 0] * 0.1) + np.cos(points[:, 1] * 0.1)

    # Create grid
    x = np.linspace(0, 100, n_grid)
    y = np.linspace(0, 100, n_grid)
    xx, yy = np.meshgrid(x, y)
    query_points = np.column_stack((xx.ravel(), yy.ravel()))

    print(
        f"Data: {n_points} points, {n_grid}x{n_grid} grid ({len(query_points)} query points)"
    )
    print("-" * 60)

    results = {
        "numpy_version": np.__version__,
        "n_points": n_points,
        "n_grid": n_grid,
    }

    # FastRBFInterpolator (Local k=30)
    print("Running FastRBFInterpolator (Local k=30)...")
    neighbors = 30

    # Scipy Baseline (Local)
    start_time = time.perf_counter()
    rbf = RBFInterpolator(
        points, values, neighbors=neighbors, kernel="linear", epsilon=1.0
    )
    _ = rbf(query_points)
    scipy_local_time = time.perf_counter() - start_time
    results["scipy_local_time"] = scipy_local_time
    print(f"Scipy RBFInterpolator (k={neighbors}): {scipy_local_time:.4f} sec")

    # FastRBF
    start_setup = time.perf_counter()
    fast_rbf = FastRBFInterpolator(neighbors=neighbors, kernel="linear")
    fast_rbf.fit(points, query_points)
    setup_time = time.perf_counter() - start_setup

    start_predict = time.perf_counter()
    _ = fast_rbf.predict(values)
    predict_time = time.perf_counter() - start_predict

    fast_total = setup_time + predict_time
    results["fast_rbf_setup_time"] = setup_time
    results["fast_rbf_predict_time"] = predict_time
    results["fast_rbf_total_time"] = fast_total

    print(
        f"FastRBFInterpolator (Total):   {fast_total:.4f} sec (Setup: {setup_time:.4f}, Predict: {predict_time:.4f})"
    )

    # Save results
    filename = f"benchmark_results_{np.__version__}.json"
    with open(filename, "w") as f:
        json.dump(results, f, indent=4)
    print(f"Results saved to {filename}")


if __name__ == "__main__":
    benchmark()
