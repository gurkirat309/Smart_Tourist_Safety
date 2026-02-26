"""
Crowd Density Risk Model
========================
Uses DBSCAN clustering to identify crowd hotspots from live tourist pings.
Maps cluster density to a 0–1 risk score based on configurable thresholds.
"""

import math
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from typing import List, Tuple, Dict

# Tuning parameters
DBSCAN_EPS_KM = 0.1          # ~100m neighbourhood radius
DBSCAN_MIN_SAMPLES = 5       # minimum tourists to form a cluster
DENSE_CROWD_THRESHOLD = 20   # cluster members above this → HIGH risk
MODERATE_CROWD_THRESHOLD = 8

# Convert degrees to km at ~28° latitude
DEG_TO_KM = 111.0            # 1° latitude ≈ 111 km


def _deg_to_km_arr(coords_deg: np.ndarray) -> np.ndarray:
    """Scale lat/lng degree coords to km for DBSCAN."""
    result = coords_deg.copy()
    result[:, 0] *= DEG_TO_KM
    result[:, 1] *= DEG_TO_KM * math.cos(math.radians(28.6))
    return result


def run_dbscan(pings: List[Dict]) -> pd.DataFrame:
    """
    Parameters
    ----------
    pings : list of {"lat": float, "lng": float, "tourist_id": int}

    Returns
    -------
    DataFrame with lat, lng, tourist_id, cluster_id, cluster_size, crowd_risk
    """
    if not pings:
        return pd.DataFrame()

    df = pd.DataFrame(pings)
    coords_deg = df[["lat", "lng"]].values
    coords_km = _deg_to_km_arr(coords_deg)

    # DBSCAN expects distance in the unit of eps; we work in km
    db = DBSCAN(eps=DBSCAN_EPS_KM, min_samples=DBSCAN_MIN_SAMPLES, algorithm="ball_tree",
                metric="euclidean")
    labels = db.fit_predict(coords_km)
    df["cluster_id"] = labels

    # Compute cluster sizes
    cluster_sizes = df.groupby("cluster_id")["cluster_id"].transform("count")
    df["cluster_size"] = cluster_sizes
    df.loc[df["cluster_id"] == -1, "cluster_size"] = 1   # noise = alone

    # Map cluster size → risk score
    def _risk_score(size: int, cid: int) -> float:
        if cid == -1:
            return 0.05   # isolated tourist
        if size >= DENSE_CROWD_THRESHOLD:
            return min(1.0, 0.7 + (size - DENSE_CROWD_THRESHOLD) * 0.01)
        if size >= MODERATE_CROWD_THRESHOLD:
            return 0.4 + (size - MODERATE_CROWD_THRESHOLD) / (DENSE_CROWD_THRESHOLD - MODERATE_CROWD_THRESHOLD) * 0.3
        return 0.1 + (size / MODERATE_CROWD_THRESHOLD) * 0.3

    df["crowd_risk"] = df.apply(lambda r: _risk_score(r["cluster_size"], r["cluster_id"]), axis=1)
    df["crowd_risk"] = df["crowd_risk"].round(4)

    return df


def get_cluster_summary(df: pd.DataFrame) -> List[Dict]:
    """
    Returns one entry per cluster with centroid and risk, useful for the Police dashboard.
    """
    if df.empty:
        return []

    summaries = []
    for cid, grp in df[df["cluster_id"] != -1].groupby("cluster_id"):
        summaries.append({
            "cluster_id":   int(cid),
            "center_lat":   round(grp["lat"].mean(), 6),
            "center_lng":   round(grp["lng"].mean(), 6),
            "tourist_count": int(len(grp)),
            "crowd_risk":   float(grp["crowd_risk"].max()),
        })
    return summaries
