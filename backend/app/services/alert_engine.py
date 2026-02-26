"""
Alert Engine Service
====================
Evaluates ML outputs and decides whether to fire an alert.
Alert logic:
  - HIGH area risk + route deviation    → CRITICAL alert
  - HIGH inactivity in medium/high zone → HIGH alert
  - EXTREME crowd density (>0.8)        → HIGH alert
  - Any single HIGH ML score            → MEDIUM alert
  - PANIC button                        → CRITICAL regardless
"""

from datetime import datetime
from typing import Optional, Dict
from sqlalchemy.orm import Session

from app.models.models import Alert, Tourist


ALERT_THRESHOLDS = {
    "area_risk_high":        2,       # risk_label == 2
    "deviation_critical":    True,
    "inactivity_high":       0.70,    # inactivity_probability
    "crowd_critical":        0.80,    # crowd_risk
    "crowd_moderate":        0.50,
}


def evaluate_and_create_alert(
    db: Session,
    tourist: Tourist,
    lat: float,
    lng: float,
    area_result: Dict,
    deviation_result: Dict,
    inactivity_result: Dict,
    crowd_risk: float,
) -> Optional[Alert]:
    """
    Runs composite alert logic. Creates and persists an Alert if triggered.
    Returns the Alert object or None.
    """
    risk_label = area_result.get("risk_label", 0)
    is_deviation = deviation_result.get("is_deviation", False)
    is_inactive = inactivity_result.get("is_inactive", False)
    inactivity_prob = inactivity_result.get("inactivity_probability", 0.0)

    alert_type = None
    severity = "medium"
    message = ""

    # ── Rule 1: CRITICAL – deviation in high-risk zone ──────────────────────
    if is_deviation and risk_label >= 2:
        alert_type = "area_risk+deviation"
        severity = "critical"
        message = (
            f"Tourist {tourist.name} has deviated {deviation_result['deviation_distance_m']:.0f}m "
            f"from planned route in a HIGH-RISK zone!"
        )

    # ── Rule 2: HIGH – suspicious inactivity in risky zone ───────────────────
    elif is_inactive and risk_label >= 1 and inactivity_prob > ALERT_THRESHOLDS["inactivity_high"]:
        alert_type = "inactivity"
        severity = "high"
        message = (
            f"Tourist {tourist.name} has been inactive for "
            f"{inactivity_result['inactivity_minutes']:.1f} min in a "
            f"{'HIGH' if risk_label == 2 else 'MEDIUM'}-risk area."
        )

    # ── Rule 3: HIGH – extreme crowd density ────────────────────────────────
    elif crowd_risk >= ALERT_THRESHOLDS["crowd_critical"]:
        alert_type = "crowd_density"
        severity = "high"
        message = (
            f"Extreme crowd density detected near tourist {tourist.name} "
            f"(risk score: {crowd_risk:.2f}). Possible stampede risk."
        )

    # ── Rule 4: MEDIUM – single high-risk signal ────────────────────────────
    elif risk_label >= 2:
        alert_type = "area_risk"
        severity = "medium"
        message = f"Tourist {tourist.name} is in a HIGH-risk zone ({area_result['risk_name']})."
    elif is_deviation:
        alert_type = "deviation"
        severity = "medium"
        message = (
            f"Tourist {tourist.name} deviated {deviation_result['deviation_distance_m']:.0f}m "
            f"from planned route."
        )
    elif crowd_risk >= ALERT_THRESHOLDS["crowd_moderate"]:
        alert_type = "crowd_density"
        severity = "low"
        message = f"Moderate crowd density near tourist {tourist.name} (risk: {crowd_risk:.2f})."

    if alert_type is None:
        return None

    alert = Alert(
        tourist_id=tourist.id,
        alert_type=alert_type,
        severity=severity,
        message=message,
        lat=lat,
        lng=lng,
        is_resolved=False,
        created_at=datetime.utcnow(),
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def create_panic_alert(db: Session, tourist: Tourist, lat: float, lng: float) -> Alert:
    """Directly creates a CRITICAL panic alert, no ML evaluation required."""
    alert = Alert(
        tourist_id=tourist.id,
        alert_type="panic",
        severity="critical",
        message=f"🚨 PANIC: Tourist {tourist.name} has triggered the emergency panic button at "
                f"({lat:.5f}, {lng:.5f})!",
        lat=lat,
        lng=lng,
        is_resolved=False,
        created_at=datetime.utcnow(),
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert
