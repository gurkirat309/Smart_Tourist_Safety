from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr


# ─── Auth ────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: str = "tourist"  # tourist | police


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    user_id: int


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


# ─── Tourist ─────────────────────────────────────────────────────────────────

class TouristCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    emergency_contact: Optional[str] = None


class TouristOut(BaseModel):
    id: int
    user_id: int
    name: str
    phone: Optional[str]
    emergency_contact: Optional[str]
    current_lat: Optional[float]
    current_lng: Optional[float]
    last_seen: Optional[datetime]
    is_active_session: bool
    panic_triggered: bool

    class Config:
        from_attributes = True


# ─── Route ───────────────────────────────────────────────────────────────────

class RouteCreate(BaseModel):
    start_lat: float
    start_lng: float
    end_lat: float
    end_lng: float
    planned_waypoints: Optional[str] = None   # JSON string


class RouteOut(BaseModel):
    id: int
    tourist_id: int
    start_lat: float
    start_lng: float
    end_lat: float
    end_lng: float
    planned_waypoints: Optional[str]
    started_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


# ─── Location ────────────────────────────────────────────────────────────────

class LocationUpdate(BaseModel):
    lat: float
    lng: float


class LocationPingOut(BaseModel):
    id: int
    tourist_id: int
    lat: float
    lng: float
    timestamp: datetime
    deviation_distance_m: float
    is_deviation: bool
    inactivity_minutes: float
    is_inactive: bool
    crowd_risk: float
    composite_risk_score: float

    class Config:
        from_attributes = True


# ─── Zone ────────────────────────────────────────────────────────────────────

class ZoneOut(BaseModel):
    id: int
    name: str
    zone_type: str
    center_lat: float
    center_lng: float
    radius_km: float
    risk_label: int
    risk_probability: float

    class Config:
        from_attributes = True


# ─── Alert ───────────────────────────────────────────────────────────────────

class AlertOut(BaseModel):
    id: int
    tourist_id: int
    alert_type: str
    severity: str
    message: str
    lat: Optional[float]
    lng: Optional[float]
    is_resolved: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Risk Status ─────────────────────────────────────────────────────────────

class RiskStatus(BaseModel):
    tourist_id: int
    current_lat: float
    current_lng: float
    area_risk_probability: float
    area_risk_label: str
    is_deviation: bool
    deviation_distance_m: float
    is_inactive: bool
    inactivity_minutes: float
    crowd_risk: float
    composite_risk_score: float
    active_alerts: List[AlertOut]
