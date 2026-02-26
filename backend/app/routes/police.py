from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_police_user
from app.models.models import User, Tourist, Zone, Alert, LocationPing
from app.schemas import AlertOut, ZoneOut, TouristOut
from app.ml_models.crowd_density import run_dbscan, get_cluster_summary

router = APIRouter(prefix="/api/police", tags=["police"])


@router.get("/tourists", response_model=List[TouristOut])
def list_tourists(db: Session = Depends(get_db),
                  _: User = Depends(get_police_user)):
    return db.query(Tourist).all()


@router.get("/tourists/{tourist_id}/location-history")
def location_history(tourist_id: int, limit: int = 50,
                     db: Session = Depends(get_db),
                     _: User = Depends(get_police_user)):
    pings = db.query(LocationPing).filter(
        LocationPing.tourist_id == tourist_id
    ).order_by(LocationPing.timestamp.desc()).limit(limit).all()
    return [{"lat": p.lat, "lng": p.lng, "timestamp": p.timestamp.isoformat(),
             "composite_risk_score": p.composite_risk_score} for p in pings]


@router.get("/zones", response_model=List[ZoneOut])
def list_zones(db: Session = Depends(get_db),
               _: User = Depends(get_police_user)):
    return db.query(Zone).all()


@router.get("/alerts", response_model=List[AlertOut])
def list_alerts(resolved: bool = False, limit: int = 100,
                db: Session = Depends(get_db),
                _: User = Depends(get_police_user)):
    return db.query(Alert).filter(
        Alert.is_resolved == resolved
    ).order_by(Alert.created_at.desc()).limit(limit).all()


@router.post("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: int, db: Session = Depends(get_db),
                  _: User = Depends(get_police_user)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_resolved = True
    alert.resolved_at = datetime.utcnow()
    db.commit()
    return {"status": "resolved", "alert_id": alert_id}


@router.get("/crowd/clusters")
def get_crowd_clusters(db: Session = Depends(get_db),
                       _: User = Depends(get_police_user)):
    """Run DBSCAN on the latest location pings and return cluster summaries."""
    pings = db.query(LocationPing).order_by(LocationPing.timestamp.desc()).limit(300).all()
    ping_dicts = [{"lat": p.lat, "lng": p.lng, "tourist_id": p.tourist_id} for p in pings]
    df = run_dbscan(ping_dicts)
    clusters = get_cluster_summary(df) if not df.empty else []
    return {"clusters": clusters, "total_tourists_analyzed": len(ping_dicts)}


@router.get("/heatmap")
def heatmap_data(db: Session = Depends(get_db),
                 _: User = Depends(get_police_user)):
    """Return all recent pings with risk scores for heatmap rendering."""
    pings = db.query(LocationPing).order_by(LocationPing.timestamp.desc()).limit(500).all()
    return [{"lat": p.lat, "lng": p.lng,
             "intensity": p.composite_risk_score} for p in pings]


@router.post("/seed-zones")
def seed_zones(db: Session = Depends(get_db),
               _: User = Depends(get_police_user)):
    """Seed the database with synthetic zone data."""
    from app.services.data_generator import generate_zone_seed_data
    if db.query(Zone).count() > 0:
        return {"status": "already_seeded", "count": db.query(Zone).count()}
    zones_data = generate_zone_seed_data()
    for zd in zones_data:
        db.add(Zone(**zd))
    db.commit()
    return {"status": "seeded", "count": len(zones_data)}
