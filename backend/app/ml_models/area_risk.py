"""
Area Risk Classifier
====================
Supervised Random Forest trained on synthetic zone-feature data.
Predicts risk_label (0=low, 1=medium, 2=high) and risk probability.
"""

import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report
from sklearn.pipeline import Pipeline

from app.services.data_generator import generate_area_risk_dataset

MODEL_PATH = os.path.join(os.path.dirname(__file__), "saved", "area_risk_model.pkl")

FEATURE_COLS = [
    "lighting_score",
    "crowd_history",
    "incident_history",
    "isolation_score",
    "time_of_day_risk",
    "police_coverage",
]

LABEL_NAMES = {0: "Low", 1: "Medium", 2: "High"}


CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "area_risk_data.csv")


def train_area_risk_model(save: bool = True) -> Pipeline:
    if os.path.exists(CSV_PATH):
        print(f"[AreaRiskModel] Loading training data from {CSV_PATH}")
        df = pd.read_csv(CSV_PATH)
    else:
        print("[AreaRiskModel] CSV not found – generating synthetic data")
        df = generate_area_risk_dataset(n_samples=3000)

    X = df[FEATURE_COLS]
    y = df["risk_label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf",    RandomForestClassifier(
            n_estimators=150,
            max_depth=8,
            class_weight="balanced",
            random_state=42,
        )),
    ])

    pipeline.fit(X_train, y_train)
    report = classification_report(y_test, pipeline.predict(X_test), target_names=["Low", "Medium", "High"])
    print("[AreaRiskModel] Trained\n", report)

    if save:
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump(pipeline, MODEL_PATH)
        print(f"[AreaRiskModel] Saved to {MODEL_PATH}")

    return pipeline


def load_area_risk_model() -> Pipeline:
    if not os.path.exists(MODEL_PATH):
        print("[AreaRiskModel] No saved model found – training now…")
        return train_area_risk_model(save=True)
    return joblib.load(MODEL_PATH)


class AreaRiskPredictor:
    def __init__(self):
        self._model: Pipeline = load_area_risk_model()

    def predict(self, zone_features: dict) -> dict:
        """
        zone_features: dict with keys matching FEATURE_COLS
        Returns: {"risk_label": int, "risk_probability": float, "risk_name": str}
        """
        df = pd.DataFrame([{col: zone_features.get(col, 0.5) for col in FEATURE_COLS}])
        label = int(self._model.predict(df)[0])
        proba = float(self._model.predict_proba(df)[0][label])
        return {
            "risk_label":       label,
            "risk_probability": round(proba, 4),
            "risk_name":        LABEL_NAMES[label],
        }
