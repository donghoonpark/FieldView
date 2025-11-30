import time
import numpy as np
from scipy.interpolate import RBFInterpolator

def profile_rbf_upscale(n_points=50, full_grid=300, low_grid=30, neighbors=30):
    print(f"Profiling RBF: Full ({full_grid}x{full_grid}) vs Low-Res ({low_grid}x{low_grid})")
    
    # Generate random data
    points = np.random.rand(n_points, 2) * 300
    values = np.random.rand(n_points)
    
    # 1. Full Resolution RBF
    x_full = np.linspace(0, 300, full_grid)
    y_full = np.linspace(0, 300, full_grid)
    X_full, Y_full = np.meshgrid(x_full, y_full)
    grid_full = np.column_stack((X_full.ravel(), Y_full.ravel()))
    
    start_full = time.perf_counter()
    interp = RBFInterpolator(points, values, neighbors=neighbors, kernel='thin_plate_spline')
    _ = interp(grid_full)
    end_full = time.perf_counter()
    time_full = end_full - start_full
    
    # 2. Low Resolution RBF
    x_low = np.linspace(0, 300, low_grid)
    y_low = np.linspace(0, 300, low_grid)
    X_low, Y_low = np.meshgrid(x_low, y_low)
    grid_low = np.column_stack((X_low.ravel(), Y_low.ravel()))
    
    start_low = time.perf_counter()
    interp_low = RBFInterpolator(points, values, neighbors=neighbors, kernel='thin_plate_spline')
    _ = interp_low(grid_low)
    end_low = time.perf_counter()
    time_low = end_low - start_low
    
    print(f"Full Res Time: {time_full:.6f} s")
    print(f"Low Res Time:  {time_low:.6f} s")
    print(f"Speedup: {time_full/time_low:.2f}x")
    print("-" * 30)

if __name__ == "__main__":
    profile_rbf_upscale(n_points=50, full_grid=300, low_grid=30, neighbors=30)
    profile_rbf_upscale(n_points=50, full_grid=300, low_grid=50, neighbors=30)
