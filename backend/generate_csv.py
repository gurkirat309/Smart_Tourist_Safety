"""
CSV Data Generator
==================
Run this script to generate training CSV files for all 3 ML models.
Output: backend/data/area_risk_data.csv
        backend/data/route_deviation_data.csv
        backend/data/inactivity_data.csv

Usage:
    cd backend
    python generate_csv.py
"""

import os
import sys
import importlib

# Add backend dir to path
sys.path.insert(0, os.path.dirname(__file__))

# Import data_generator directly to avoid __init__.py pulling in DB deps
spec = importlib.util.spec_from_file_location(
    "data_generator",
    os.path.join(os.path.dirname(__file__), "app", "services", "data_generator.py"),
)
data_generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(data_generator)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    # 1. Area Risk Dataset
    print("[1/3] Generating Area Risk dataset …")
    df_area = data_generator.generate_area_risk_dataset(n_samples=3000)
    path_area = os.path.join(DATA_DIR, "area_risk_data.csv")
    df_area.to_csv(path_area, index=False)
    print(f"  ✅ Saved {len(df_area)} rows → {path_area}")

    # 2. Route Deviation Dataset
    print("[2/3] Generating Route Deviation dataset …")
    df_route = data_generator.generate_route_deviation_dataset(n_normal=1500, n_anomaly=300)
    path_route = os.path.join(DATA_DIR, "route_deviation_data.csv")
    df_route.to_csv(path_route, index=False)
    print(f" Saved {len(df_route)} rows → {path_route}")

    # 3. Inactivity Dataset
    print("[3/3] Generating Inactivity dataset …")
    df_inac = data_generator.generate_inactivity_dataset(n_samples=3000)
    path_inac = os.path.join(DATA_DIR, "inactivity_data.csv")
    df_inac.to_csv(path_inac, index=False)
    print(f"Saved {len(df_inac)} rows → {path_inac}")

    print("\nCSV files are generated successfully in backend/data/")


if __name__ == "__main__":
    main()
