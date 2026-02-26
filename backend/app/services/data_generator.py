"""
Synthetic Data Generator Service
=================================
Generates all synthetic data needed to:
  1. Seed the database with zones and tourist profiles
  2. Produce training datasets for ML models
  3. Simulate continuous tourist movement for live testing

NO external APIs are used. All data is fabricated using numpy/shapely/random.
"""

import json
import math
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Tuple, Dict

import numpy as np
import pandas as pd

# ──────────────────────────────────────────────────────────────────────────────
# City Grid – Base city centred at a fictional tourist destination
# ──────────────────────────────────────────────────────────────────────────────
BASE_LAT = 28.6139   # New Delhi-like coordinate
BASE_LNG = 77.2090
CITY_SPREAD_DEG = 0.10   # ~11 km radius

ZONE_TYPES = ["urban", "market", "park", "beach", "historical", "suburb", "industrial"]

ZONE_DEFINITIONS = [
    # (name, type, center_lat_offset, center_lng_offset, lighting, crowd_hist, incident_hist, isolation, time_risk, police)
    ("Old City Market",   "market",     -0.02,  0.01, 0.4, 0.9, 0.6, 0.2, 0.7, 0.3),
    ("Central Park",      "park",        0.01, -0.01, 0.7, 0.5, 0.1, 0.3, 0.2, 0.6),
    ("Heritage District", "historical",  0.03,  0.02, 0.5, 0.7, 0.3, 0.1, 0.4, 0.5),
    ("Riverside Walk",    "park",       -0.04,  0.03, 0.3, 0.3, 0.4, 0.5, 0.6, 0.2),
    ("Tourist Bazaar",    "market",      0.00,  0.04, 0.8, 0.8, 0.2, 0.1, 0.3, 0.7),
    ("South Suburb",      "suburb",     -0.05, -0.03, 0.6, 0.2, 0.1, 0.6, 0.2, 0.4),
    ("Industrial Zone",   "industrial",  0.06, -0.05, 0.1, 0.1, 0.8, 0.9, 0.9, 0.1),
    ("Night Market",      "market",      0.02,  0.06, 0.5, 0.9, 0.5, 0.2, 0.8, 0.3),
    ("Hilltop Resort",    "historical", -0.03, -0.06, 0.6, 0.4, 0.1, 0.7, 0.3, 0.3),
    ("Beach Front",       "beach",       0.05,  0.00, 0.8, 0.6, 0.2, 0.4, 0.4, 0.5),
]


def generate_zone_seed_data() -> List[Dict]:
    """Return a list of dicts suitable for seeding the Zone table."""
    zones = []
    for zdef in ZONE_DEFINITIONS:
        name, ztype, dlat, dlng, lighting, crowd, incident, isolation, time_risk, police = zdef
        zones.append({
            "name": name,
            "zone_type": ztype,
            "center_lat": round(BASE_LAT + dlat, 6),
            "center_lng": round(BASE_LNG + dlng, 6),
            "radius_km": round(random.uniform(0.3, 1.2), 2),
            "lighting_score": lighting,
            "crowd_history": crowd,
            "incident_history": incident,
            "isolation_score": isolation,
            "time_of_day_risk": time_risk,
            "police_coverage": police,
        })
    return zones


# ──────────────────────────────────────────────────────────────────────────────
# Training Dataset for Area Risk Classifier
# ──────────────────────────────────────────────────────────────────────────────

def _compute_risk_label(row: pd.Series) -> int:
    """
    Heuristic → risk_label  (0=low, 1=medium, 2=high)
    Replicates domain knowledge that feeds the supervised classifier.
    """
    score = (
        (1 - row["lighting_score"]) * 0.25
        + row["incident_history"] * 0.35
        + row["isolation_score"] * 0.15
        + row["time_of_day_risk"] * 0.15
        + (1 - row["police_coverage"]) * 0.10
    )
    if score < 0.3:
        return 0  # low
    elif score < 0.6:
        return 1  # medium
    return 2      # high


def generate_area_risk_dataset(n_samples: int = 2000) -> pd.DataFrame:
    """
    Generates a synthetic tabular dataset for training the Area Risk Classifier.
    Each row represents one zone observation at a point in time.
    """
    rng = np.random.default_rng(42)

    df = pd.DataFrame({
        "lighting_score":   rng.uniform(0.0, 1.0, n_samples),
        "crowd_history":    rng.uniform(0.0, 1.0, n_samples),
        "incident_history": rng.beta(2, 5, n_samples),     # skewed low – most zones are safe
        "isolation_score":  rng.uniform(0.0, 1.0, n_samples),
        "time_of_day_risk": rng.uniform(0.0, 1.0, n_samples),
        "police_coverage":  rng.uniform(0.0, 1.0, n_samples),
    })

    df["risk_label"] = df.apply(_compute_risk_label, axis=1)
    return df


# ──────────────────────────────────────────────────────────────────────────────
# Route Simulation Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _meters_to_deg(meters: float, reference_lat: float) -> Tuple[float, float]:
    """Convert metres into approximate lat/lng degrees."""
    lat_deg = meters / 111_000
    lng_deg = meters / (111_000 * math.cos(math.radians(reference_lat)))
    return lat_deg, lng_deg


def _generate_waypoints(start: Tuple[float, float], end: Tuple[float, float],
                         n_points: int = 10) -> List[Tuple[float, float]]:
    """Linearly interpolate waypoints with small Gaussian noise."""
    lats = np.linspace(start[0], end[0], n_points)
    lngs = np.linspace(start[1], end[1], n_points)
    noise_lat = np.random.normal(0, 0.0001, n_points)
    noise_lng = np.random.normal(0, 0.0001, n_points)
    return list(zip((lats + noise_lat).round(6), (lngs + noise_lng).round(6)))


# ──────────────────────────────────────────────────────────────────────────────
# Training Dataset for Route Deviation Model (Isolation Forest)
# ──────────────────────────────────────────────────────────────────────────────

def generate_route_deviation_dataset(n_normal: int = 1500,
                                      n_anomaly: int = 300) -> pd.DataFrame:
    """
    Each row represents one real ping against its nearest planned path point.

    Features:
      - deviation_m: perpendicular distance from the planned route in metres
      - speed_kmh:   instantaneous speed between last two pings
      - heading_change_deg: sudden direction changes > 90° are suspicious

    Labels (for evaluation): 0=normal, 1=deviation
    """
    rng = np.random.default_rng(99)

    # Normal movement – small residual deviations
    normal = pd.DataFrame({
        "deviation_m":        rng.exponential(scale=12, size=n_normal).clip(0, 60),
        "speed_kmh":          rng.normal(loc=5.0, scale=1.5, size=n_normal).clip(0.5, 8),
        "heading_change_deg": rng.normal(loc=0, scale=15, size=n_normal).clip(-45, 45),
    })
    normal["label"] = 0

    # Anomalous – large deviation, erratic speed, sharp direction change
    anomaly = pd.DataFrame({
        "deviation_m":        rng.uniform(80, 500, n_anomaly),
        "speed_kmh":          rng.choice(
                                  np.concatenate([
                                      rng.uniform(0.0, 0.3, n_anomaly // 2),   # stopped
                                      rng.uniform(15, 40, n_anomaly // 2),     # too fast (vehicle)
                                  ]), n_anomaly, replace=False),
        "heading_change_deg": rng.uniform(90, 180, n_anomaly),
    })
    anomaly["label"] = 1

    df = pd.concat([normal, anomaly], ignore_index=True).sample(frac=1, random_state=7)
    return df


# ──────────────────────────────────────────────────────────────────────────────
# Training Dataset for Inactivity Model
# ──────────────────────────────────────────────────────────────────────────────

def generate_inactivity_dataset(n_samples: int = 2000) -> pd.DataFrame:
    """
    Inactivity is detected via time-series anomaly features.

    Features:
      - inactivity_minutes: how long a tourist hasn't moved (>5m)
      - zone_risk_label:     risk level of the zone they're stuck in
      - time_of_day:         normalised 0.0 (midnight) – 1.0 (23:59)
      - expected_stop:       1 if tourist is at a known restaurant/sight; 0 otherwise

    Labels: 0=normal_stop, 1=suspicious_inactivity
    """
    rng = np.random.default_rng(7)

    rows = []
    for _ in range(n_samples):
        zone_risk = rng.integers(0, 3)
        time_of_day = rng.uniform(0, 1)
        expected_stop = rng.integers(0, 2)

        if expected_stop == 1:
            # Legitimate stop: restaurants, sights – can be long
            inactivity = rng.exponential(scale=20)
            label = 0
        elif zone_risk == 0:
            # Low-risk zone: longer inactivity tolerated
            inactivity = rng.exponential(scale=10)
            label = 1 if inactivity > 45 else 0
        elif zone_risk == 1:
            inactivity = rng.exponential(scale=8)
            label = 1 if inactivity > 20 else 0
        else:
            # High-risk zone: very low tolerance
            inactivity = rng.exponential(scale=5)
            label = 1 if inactivity > 10 else 0

        rows.append({
            "inactivity_minutes":  round(inactivity, 2),
            "zone_risk_label":     zone_risk,
            "time_of_day":         round(time_of_day, 4),
            "expected_stop":       expected_stop,
            "label":               label,
        })

    return pd.DataFrame(rows)


# ──────────────────────────────────────────────────────────────────────────────
# Training Dataset for Crowd Density Model (DBSCAN features)
# ──────────────────────────────────────────────────────────────────────────────

def generate_crowd_density_dataset(n_pings: int = 3000) -> pd.DataFrame:
    """
    Generates a snapshot of tourist coordinates for crowd clustering.
    Returns both lat/lng and a 'density_risk' label (0=sparse, 1=moderate, 2=dense).
    DBSCAN itself is run at inference time; this dataset trains the risk score mapper.
    """
    rng = np.random.default_rng(13)
    rows = []

    # Cluster centres (hotspots)
    hotspots = [
        (BASE_LAT - 0.02, BASE_LNG + 0.01, 0.0005, 400),   # Old City Market – always busy
        (BASE_LAT + 0.00, BASE_LNG + 0.04, 0.0004, 200),   # Tourist Bazaar
        (BASE_LAT + 0.02, BASE_LNG + 0.06, 0.0003, 150),   # Night Market
        (BASE_LAT + 0.01, BASE_LNG - 0.01, 0.0008, 150),   # Central Park – spread
        (BASE_LAT + 0.05, BASE_LNG + 0.00, 0.0006, 100),   # Beach Front
    ]

    for center_lat, center_lng, spread, count in hotspots:
        n = min(count, n_pings // len(hotspots))
        lats = rng.normal(center_lat, spread, n)
        lngs = rng.normal(center_lng, spread, n)
        rows.extend({"lat": la, "lng": lo} for la, lo in zip(lats, lngs))

    # Background scattered tourists
    n_scatter = n_pings - len(rows)
    lats = rng.uniform(BASE_LAT - 0.08, BASE_LAT + 0.08, n_scatter)
    lngs = rng.uniform(BASE_LNG - 0.08, BASE_LNG + 0.08, n_scatter)
    rows.extend({"lat": la, "lng": lo} for la, lo in zip(lats, lngs))

    df = pd.DataFrame(rows)
    df["lat"] = df["lat"].round(6)
    df["lng"] = df["lng"].round(6)
    return df


# ──────────────────────────────────────────────────────────────────────────────
# Live Movement Simulator  (used by the WebSocket broadcaster)
# ──────────────────────────────────────────────────────────────────────────────

class LiveTouristSimulator:
    """
    Generates continuous location pings for a synthetic tourist session.
    Call next_ping() each tick to get a new (lat, lng, is_anomaly) tuple.
    """

    def __init__(self, tourist_id: int, zone: Dict):
        self.tourist_id = tourist_id
        self.zone = zone
        center = (zone["center_lat"], zone["center_lng"])
        spread = 0.005

        # Generate planned route within zone
        start = (center[0] + random.uniform(-spread, spread),
                 center[1] + random.uniform(-spread, spread))
        end   = (center[0] + random.uniform(-spread, spread),
                 center[1] + random.uniform(-spread, spread))
        self.waypoints = _generate_waypoints(start, end, n_points=20)
        self.step = 0
        self.inactive_ticks = 0
        self.force_anomaly_at = random.randint(8, 16)   # inject anomaly mid-route
        self.anomaly_type = random.choice(["deviation", "inactivity"])

    def next_ping(self) -> Tuple[float, float, str]:
        """Return (lat, lng, anomaly_type_or_none)."""
        if self.step >= len(self.waypoints):
            # Loop the route
            self.step = 0
            self.inactive_ticks = 0

        anomaly = None

        if self.step == self.force_anomaly_at:
            if self.anomaly_type == "deviation":
                # Jump off-route
                base = self.waypoints[self.step]
                lat = base[0] + random.uniform(0.008, 0.015)
                lng = base[1] + random.uniform(0.008, 0.015)
                anomaly = "deviation"
            else:
                # Stay frozen
                wp = self.waypoints[self.step]
                self.inactive_ticks += 1
                if self.inactive_ticks > 5:
                    anomaly = "inactivity"
                lat, lng = wp
        else:
            wp = self.waypoints[self.step]
            lat = wp[0] + random.gauss(0, 0.00005)
            lng = wp[1] + random.gauss(0, 0.00005)
            self.step += 1
            self.inactive_ticks = 0

        return round(lat, 6), round(lng, 6), anomaly


def get_all_simulators(zones: List[Dict], n_tourists: int = 6) -> List[LiveTouristSimulator]:
    """Create n_tourists simulators assigned to random zones."""
    simulators = []
    for i in range(n_tourists):
        zone = random.choice(zones)
        simulators.append(LiveTouristSimulator(tourist_id=i + 1, zone=zone))
    return simulators
