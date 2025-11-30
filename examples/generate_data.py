import numpy as np
import pandas as pd
import os

def generate_dummy_data(filename="dummy_data.csv", n_points=50, radius=150):
    """
    Generates dummy data with a gradient pattern and saves it to a CSV file.
    """
    # Generate random points in square range [-150, 150]
    x = (np.random.rand(n_points) - 0.5) * 2 * radius
    y = (np.random.rand(n_points) - 0.5) * 2 * radius
    
    # Generate values with a gradient (Left -> Right)
    normalized_x = (x + radius) / (2 * radius)
    base_values = normalized_x * 80
    noise = (np.random.rand(n_points) - 0.5) * 20
    values = base_values + noise
    values = np.clip(values, 0, 100)
    
    df = pd.DataFrame({
        'x': x,
        'y': y,
        'value': values
    })
    
    df.to_csv(filename, index=False)
    print(f"Generated {n_points} points to {filename}")
    return df

if __name__ == "__main__":
    generate_dummy_data()
