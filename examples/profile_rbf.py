import time
import numpy as np
from scipy.interpolate import RBFInterpolator

def profile_rbf(n_points=100, grid_size=300, neighbors=30):
    print(f"Profiling RBF Interpolator with {n_points} points, {grid_size}x{grid_size} grid, neighbors={neighbors}")
    
    # Generate random data
    points = np.random.rand(n_points, 2) * 300
    values = np.random.rand(n_points)
    
    # Generate grid
    x = np.linspace(0, 300, grid_size)
    y = np.linspace(0, 300, grid_size)
    X, Y = np.meshgrid(x, y)
    grid_points = np.column_stack((X.ravel(), Y.ravel()))
    
    # 1. Fitting (Kernel Creation)
    start_fit = time.perf_counter()
    interp = RBFInterpolator(points, values, neighbors=neighbors, kernel='thin_plate_spline')
    end_fit = time.perf_counter()
    fit_time = end_fit - start_fit
    
    # 2. Evaluation (Pixel Calculation)
    start_eval = time.perf_counter()
    _ = interp(grid_points)
    end_eval = time.perf_counter()
    eval_time = end_eval - start_eval
    
    print(f"Fitting Time: {fit_time:.6f} s")
    print(f"Evaluation Time: {eval_time:.6f} s")
    print(f"Ratio (Eval/Fit): {eval_time/fit_time:.2f}")
    print("-" * 30)

if __name__ == "__main__":
    # Scenario 1: Typical usage in demo
    profile_rbf(n_points=50, grid_size=300, neighbors=30)
    
    # Scenario 2: More points
    profile_rbf(n_points=200, grid_size=300, neighbors=30)
    
    # Scenario 3: Global RBF (neighbors=None)
    profile_rbf(n_points=50, grid_size=300, neighbors=None)
