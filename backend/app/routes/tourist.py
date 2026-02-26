import json
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user, get_tourist_user
from app.models.models import User, Tourist, Route, LocationPing, Alert
from app.schemas import (
    TouristOut, RouteCreate, RouteOut,
    LocationUpdate, LocationPingOut, RiskStatus, AlertOut
)
from app.services.alert_engine import evaluate_and_create_alert, create_panic_alert
from app.services.websocket_manager import manager

router = APIRouter(prefix="/api/tourist", tags=["tourist"])

# Lazy singletons — initialised on first request, NOT at import time
_area_model = None
_dev_model = None
_inac_model = None


def _get_models():
    global _area_model, _dev_model, _inac_model
    if _area_model is None:
        from app.ml_models.area_risk import AreaRiskPredictor
        from app.ml_models.route_deviation import RouteDeviationDetector
        from app.ml_models.inactivity import InactivityDetector
        _area_model = AreaRiskPredictor()
        _dev_model = RouteDeviationDetector()
        _inac_model = InactivityDetector()
    return _area_model, _dev_model, _inac_model


def _get_tourist(user: User, db: Session) -> Tourist:
    tourist = db.query(Tourist).filter(Tourist.user_id == user.id).first()
    if not tourist:
        raise HTTPException(status_code=404, detail="Tourist profile not found")
    return tourist


@router.get("/profile", response_model=TouristOut)
def get_profile(current_user: User = Depends(get_tourist_user),
                db: Session = Depends(get_db)):
    return _get_tourist(current_user, db)


@router.post("/route/start", response_model=RouteOut)
def start_route(route_data: RouteCreate,
                current_user: User = Depends(get_tourist_user),
                db: Session = Depends(get_db)):
    tourist = _get_tourist(current_user, db)
    # End any active route
    db.query(Route).filter(Route.tourist_id == tourist.id, Route.is_active == True).update(
        {"is_active": False, "ended_at": datetime.utcnow()}
    )
    route = Route(
        tourist_id=tourist.id,
        start_lat=route_data.start_lat,
        start_lng=route_data.start_lng,
        end_lat=route_data.end_lat,
        end_lng=route_data.end_lng,
        planned_waypoints=route_data.planned_waypoints,
        is_active=True,
    )
    tourist.is_active_session = True
    db.add(route)
    db.commit()
    db.refresh(route)
    return route


@router.post("/location/update", response_model=LocationPingOut)
async def update_location(loc: LocationUpdate,
                           current_user: User = Depends(get_tourist_user),
                           db: Session = Depends(get_db)):
    tourist = _get_tourist(current_user, db)
    lat, lng = loc.lat, loc.lng
    area_model, dev_model, inac_model = _get_models()

    # ── 1. Area Risk ─────────────────────────────────────────────────────────
    from app.models.models import Zone
    # Find closest zone
    zones = db.query(Zone).all()
    closest_zone = None
    min_dist = float("inf")
    for z in zones:
        from app.ml_models.route_deviation import haversine_meters
        d = haversine_meters(lat, lng, z.center_lat, z.center_lng)
        if d < min_dist:
            min_dist = d
            closest_zone = z

    zone_features = {}
    zone_id = None
    zone_risk_label = 0
    if closest_zone:
        zone_id = closest_zone.id
        zone_features = {
            "lighting_score":   closest_zone.lighting_score,
            "crowd_history":    closest_zone.crowd_history,
            "incident_history": closest_zone.incident_history,
            "isolation_score":  closest_zone.isolation_score,
            "time_of_day_risk": closest_zone.time_of_day_risk,
            "police_coverage":  closest_zone.police_coverage,
        }
    area_result = area_model.predict(zone_features)
    zone_risk_label = area_result["risk_label"]

    # Update zone risk in DB
    if closest_zone:
        closest_zone.risk_label = zone_risk_label
        closest_zone.risk_probability = area_result["risk_probability"]
        db.add(closest_zone)

    # ── 2. Route Deviation ───────────────────────────────────────────────────
    active_route = db.query(Route).filter(
        Route.tourist_id == tourist.id, Route.is_active == True
    ).first()

    waypoints = []
    if active_route and active_route.planned_waypoints:
        try:
            waypoints = json.loads(active_route.planned_waypoints)
        except Exception:
            waypoints = []

    # Previous ping for speed/heading
    last_ping = db.query(LocationPing).filter(
        LocationPing.tourist_id == tourist.id
    ).order_by(LocationPing.timestamp.desc()).first()

    prev_lat = last_ping.lat if last_ping else None
    prev_lng = last_ping.lng if last_ping else None

    dev_result = dev_model.analyze(lat, lng, waypoints, prev_lat, prev_lng)

    # ── 3. Inactivity ────────────────────────────────────────────────────────
    inactivity_minutes = 0.0
    if tourist.last_seen:
        delta = datetime.utcnow() - tourist.last_seen
        inactivity_minutes = delta.total_seconds() / 60.0

    now = datetime.utcnow()
    time_of_day = (now.hour * 60 + now.minute) / (24 * 60)
    inac_result = inac_model.analyze(
        inactivity_minutes=inactivity_minutes,
        zone_risk_label=zone_risk_label,
        time_of_day=time_of_day,
        expected_stop=0,
    )

    # ── 4. Crowd Density ─────────────────────────────────────────────────────
    from app.ml_models.crowd_density import run_dbscan
    all_pings = db.query(LocationPing).order_by(LocationPing.timestamp.desc()).limit(200).all()
    live_pings = [{"lat": p.lat, "lng": p.lng, "tourist_id": p.tourist_id} for p in all_pings]
    live_pings.append({"lat": lat, "lng": lng, "tourist_id": tourist.id})
    crowd_df = run_dbscan(live_pings)

    crowd_risk = 0.0
    if not crowd_df.empty:
        my_rows = crowd_df[crowd_df["tourist_id"] == tourist.id]
        if not my_rows.empty:
            crowd_risk = float(my_rows["crowd_risk"].max())

    # ── Composite Risk Score ─────────────────────────────────────────────────
    composite = (
        area_result["risk_probability"] * 0.35
        + (1.0 if dev_result["is_deviation"] else 0.0) * 0.25
        + inac_result["inactivity_probability"] * 0.20
        + crowd_risk * 0.20
    )

    # ── Persist Ping ─────────────────────────────────────────────────────────
    ping = LocationPing(
        tourist_id=tourist.id,
        zone_id=zone_id,
        lat=lat,
        lng=lng,
        deviation_distance_m=dev_result["deviation_distance_m"],
        is_deviation=dev_result["is_deviation"],
        inactivity_minutes=inactivity_minutes,
        is_inactive=inac_result["is_inactive"],
        crowd_risk=crowd_risk,
        composite_risk_score=round(composite, 4),
    )
    db.add(ping)

    tourist.current_lat = lat
    tourist.current_lng = lng
    tourist.last_seen = datetime.utcnow()
    db.add(tourist)
    db.commit()
    db.refresh(ping)

    # ── Alert Evaluation ─────────────────────────────────────────────────────
    alert = evaluate_and_create_alert(
        db=db, tourist=tourist, lat=lat, lng=lng,
        area_result=area_result, deviation_result=dev_result,
        inactivity_result=inac_result, crowd_risk=crowd_risk,
    )

    # ── WebSocket Broadcast ──────────────────────────────────────────────────
    import asyncio
    asyncio.create_task(
        manager.emit_location_update(
            tourist_id=tourist.id, name=tourist.name,
            lat=lat, lng=lng,
            risk_score=composite,
            is_deviation=dev_result["is_deviation"],
            is_inactive=inac_result["is_inactive"],
            crowd_risk=crowd_risk,
        )
    )
    if alert:
        asyncio.create_task(manager.emit_alert({
            "id": alert.id,
            "tourist_id": alert.tourist_id,
            "alert_type": alert.alert_type,
            "severity":   alert.severity,
            "message":    alert.message,
            "lat": alert.lat, "lng": alert.lng,
            "created_at": alert.created_at.isoformat(),
        }))

    return ping


@router.get("/risk-status", response_model=RiskStatus)
def get_risk_status(current_user: User = Depends(get_tourist_user),
                    db: Session = Depends(get_db)):
    tourist = _get_tourist(current_user, db)
    last_ping = db.query(LocationPing).filter(
        LocationPing.tourist_id == tourist.id
    ).order_by(LocationPing.timestamp.desc()).first()

    if not last_ping:
        raise HTTPException(status_code=404, detail="No location data yet")

    active_alerts = db.query(Alert).filter(
        Alert.tourist_id == tourist.id, Alert.is_resolved == False
    ).order_by(Alert.created_at.desc()).limit(10).all()

    from app.models.models import Zone
    zone = db.query(Zone).filter(Zone.id == last_ping.zone_id).first()

    return RiskStatus(
        tourist_id=tourist.id,
        current_lat=last_ping.lat,
        current_lng=last_ping.lng,
        area_risk_probability=zone.risk_probability if zone else 0.0,
        area_risk_label=["Low", "Medium", "High"][zone.risk_label] if zone else "Low",
        is_deviation=last_ping.is_deviation,
        deviation_distance_m=last_ping.deviation_distance_m,
        is_inactive=last_ping.is_inactive,
        inactivity_minutes=last_ping.inactivity_minutes,
        crowd_risk=last_ping.crowd_risk,
        composite_risk_score=last_ping.composite_risk_score,
        active_alerts=[AlertOut.model_validate(a) for a in active_alerts],
    )


@router.post("/panic")
async def panic_alert(current_user: User = Depends(get_tourist_user),
                      db: Session = Depends(get_db)):
    tourist = _get_tourist(current_user, db)
    lat = tourist.current_lat or 0.0
    lng = tourist.current_lng or 0.0
    tourist.panic_triggered = True
    db.commit()
    alert = create_panic_alert(db, tourist, lat, lng)
    import asyncio
    asyncio.create_task(manager.emit_alert({
        "id": alert.id,
        "tourist_id": alert.tourist_id,
        "alert_type": "panic",
        "severity":   "critical",
        "message":    alert.message,
        "lat": lat, "lng": lng,
        "created_at": alert.created_at.isoformat(),
    }))
    return {"status": "panic_sent", "alert_id": alert.id}
