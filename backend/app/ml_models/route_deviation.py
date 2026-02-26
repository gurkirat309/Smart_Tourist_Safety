"""
Route Deviation Model
=====================
Isolation Forest anomaly detector trained on synthetic movement data.
Flags pings where the tourist has deviated abnormally from their planned route.
"""

import math
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

from app.services.data_generator import generate_route_deviation_dataset

MODEL_PATH = os.path.join(os.path.dirname(__file__), "saved", "route_deviation_model.pkl")

FEATURE_COLS = ["deviation_m", "speed_kmh", "heading_change_deg"]
DEVIATION_THRESHOLD_M = 75.0    # metres beyond which we flag as deviation


def haversine_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Compute distance between two GPS coordinates in metres."""
    R = 6_371_000  # Earth radius in metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def nearest_waypoint_distance(lat: float, lng: float,
                               waypoints: list) -> float:
    """Find the minimum distance (metres) from a ping to any planned waypoint."""
    if not waypoints:
        return 0.0
    return min(haversine_meters(lat, lng, wp[0], wp[1]) for wp in waypoints)


def compute_heading(lat1, lng1, lat2, lng2) -> float:
    """Compute heading change magnitude between two GPS points."""
    dlng = lng2 - lng1
    dlat = lat2 - lat1
    return abs(math.degrees(math.atan2(dlng, dlat)))


def train_deviation_model(save: bool = True) -> Pipeline:
    df = generate_route_deviation_dataset()

    # Train IsolationForest on features only (unsupervised)
    X = df[FEATURE_COLS]

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf",    IsolationForest(
            n_estimators=200,
            contamination=0.15,
            random_state=42,
        )),
    ])

    pipeline.fit(X)
    print("[RouteDeviationModel] IsolationForest trained.")

    if save:
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump(pipeline, MODEL_PATH)
        print(f"[RouteDeviationModel] Saved to {MODEL_PATH}")

    return pipeline


def load_deviation_model() -> Pipeline:
    if not os.path.exists(MODEL_PATH):
        return train_deviation_model(save=True)
    return joblib.load(MODEL_PATH)


class RouteDeviationDetector:
    def __init__(self):
        self._model: Pipeline = load_deviation_model()

    def analyze(self, lat: float, lng: float,
                planned_waypoints: list,
                prev_lat: float = None, prev_lng: float = None) -> dict:
        """
        Returns:
          - deviation_distance_m: distance from nearest waypoint
          - is_deviation: bool (True if model + threshold both flag it)
          - speed_kmh: estimated speed (0 if no previous point)
          - heading_change_deg: heading magnitude
        """
        deviation_m = nearest_waypoint_distance(lat, lng, planned_waypoints)

        # Estimate speed / heading from last ping
        if prev_lat is not None and prev_lng is not None:
            dist_m = haversine_meters(prev_lat, prev_lng, lat, lng)
            speed_kmh = dist_m * 3.6 / 5  # assume 5-second ping interval
            heading_deg = compute_heading(prev_lat, prev_lng, lat, lng)
        else:
            speed_kmh = 0.0
            heading_deg = 0.0

        features = pd.DataFrame([{
            "deviation_m":        deviation_m,
            "speed_kmh":          speed_kmh,
            "heading_change_deg": heading_deg,
        }])

        # IsolationForest: -1 = anomaly, 1 = normal
        iso_flag = self._model.predict(features)[0] == -1
        threshold_flag = deviation_m > DEVIATION_THRESHOLD_M

        return {
            "deviation_distance_m": round(deviation_m, 2),
            "is_deviation":         bool(iso_flag or threshold_flag),
            "speed_kmh":            round(speed_kmh, 2),
            "heading_change_deg":   round(heading_deg, 2),
        }
