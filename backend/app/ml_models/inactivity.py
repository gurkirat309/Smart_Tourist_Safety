"""
Inactivity / Drop-off Detection Model
======================================
Uses a Gradient Boosting classifier trained on synthetic inactivity data.
Flags tourists who have been stationary for too long in a risky zone.
"""

import os
import joblib
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report

from app.services.data_generator import generate_inactivity_dataset

MODEL_PATH = os.path.join(os.path.dirname(__file__), "saved", "inactivity_model.pkl")

FEATURE_COLS = [
    "inactivity_minutes",
    "zone_risk_label",
    "time_of_day",
    "expected_stop",
]


CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "inactivity_data.csv")


def train_inactivity_model(save: bool = True) -> Pipeline:
    if os.path.exists(CSV_PATH):
        print(f"[InactivityModel] Loading training data from {CSV_PATH}")
        df = pd.read_csv(CSV_PATH)
    else:
        print("[InactivityModel] CSV not found – generating synthetic data")
        df = generate_inactivity_dataset(n_samples=3000)

    X = df[FEATURE_COLS]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf",    GradientBoostingClassifier(
            n_estimators=120,
            learning_rate=0.08,
            max_depth=4,
            random_state=42,
        )),
    ])

    pipeline.fit(X_train, y_train)
    report = classification_report(y_test, pipeline.predict(X_test),
                                   target_names=["Normal", "Suspicious"])
    print("[InactivityModel] Trained\n", report)

    if save:
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump(pipeline, MODEL_PATH)
        print(f"[InactivityModel] Saved to {MODEL_PATH}")

    return pipeline


def load_inactivity_model() -> Pipeline:
    if not os.path.exists(MODEL_PATH):
        return train_inactivity_model(save=True)
    return joblib.load(MODEL_PATH)


class InactivityDetector:
    def __init__(self):
        self._model: Pipeline = load_inactivity_model()

    def analyze(self,
                inactivity_minutes: float,
                zone_risk_label: int,
                time_of_day: float,
                expected_stop: int = 0) -> dict:
        """
        Parameters
        ----------
        inactivity_minutes : minutes since last meaningful movement
        zone_risk_label    : 0=low, 1=medium, 2=high (from AreaRiskPredictor)
        time_of_day        : 0.0–1.0 fraction of 24-hour day
        expected_stop      : 1 if tourist is at a known POI, else 0

        Returns
        -------
        dict with is_inactive (bool) and inactivity_probability (float)
        """
        features = pd.DataFrame([{
            "inactivity_minutes": inactivity_minutes,
            "zone_risk_label":    zone_risk_label,
            "time_of_day":        time_of_day,
            "expected_stop":      expected_stop,
        }])

        label = int(self._model.predict(features)[0])
        proba = float(self._model.predict_proba(features)[0][1])

        return {
            "is_inactive":             bool(label == 1),
            "inactivity_probability":  round(proba, 4),
            "inactivity_minutes":      round(inactivity_minutes, 2),
        }
