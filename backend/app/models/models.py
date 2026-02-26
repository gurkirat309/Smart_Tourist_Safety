import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, ForeignKey, Enum, Text
)
from sqlalchemy.orm import relationship
from app.database import Base


class UserRole(str, enum.Enum):
    tourist = "tourist"
    police = "police"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.tourist, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    tourist_profile = relationship("Tourist", back_populates="user", uselist=False)


class Tourist(Base):
    __tablename__ = "tourists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    name = Column(String, nullable=False)
    phone = Column(String)
    emergency_contact = Column(String)
    current_lat = Column(Float)
    current_lng = Column(Float)
    last_seen = Column(DateTime)
    is_active_session = Column(Boolean, default=False)
    panic_triggered = Column(Boolean, default=False)

    user = relationship("User", back_populates="tourist_profile")
    locations = relationship("LocationPing", back_populates="tourist")
    routes = relationship("Route", back_populates="tourist")


class Zone(Base):
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    zone_type = Column(String, default="urban")  # urban, park, beach, market
    center_lat = Column(Float, nullable=False)
    center_lng = Column(Float, nullable=False)
    radius_km = Column(Float, default=0.5)

    # Risk features (used by ML)
    lighting_score = Column(Float, default=0.5)       # 0=dark, 1=bright
    crowd_history = Column(Float, default=0.5)        # 0=empty, 1=always packed
    incident_history = Column(Float, default=0.0)     # 0=none, 1=many incidents
    isolation_score = Column(Float, default=0.5)      # 0=central, 1=isolated
    time_of_day_risk = Column(Float, default=0.3)     # 0=safe at all times, 1=night risky
    police_coverage = Column(Float, default=0.5)      # 0=no patrol, 1=heavy patrol

    # Computed / ML-assigned
    risk_label = Column(Integer, default=0)           # 0=low, 1=medium, 2=high
    risk_probability = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    location_pings = relationship("LocationPing", back_populates="zone")


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    tourist_id = Column(Integer, ForeignKey("tourists.id"), nullable=False)
    start_lat = Column(Float, nullable=False)
    start_lng = Column(Float, nullable=False)
    end_lat = Column(Float, nullable=False)
    end_lng = Column(Float, nullable=False)
    planned_waypoints = Column(Text)  # JSON string of [[lat,lng], ...]
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
    is_active = Column(Boolean, default=True)

    tourist = relationship("Tourist", back_populates="routes")


class LocationPing(Base):
    __tablename__ = "location_pings"

    id = Column(Integer, primary_key=True, index=True)
    tourist_id = Column(Integer, ForeignKey("tourists.id"), nullable=False)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # ML-computed fields
    deviation_distance_m = Column(Float, default=0.0)
    is_deviation = Column(Boolean, default=False)
    inactivity_minutes = Column(Float, default=0.0)
    is_inactive = Column(Boolean, default=False)
    crowd_risk = Column(Float, default=0.0)
    composite_risk_score = Column(Float, default=0.0)

    tourist = relationship("Tourist", back_populates="locations")
    zone = relationship("Zone", back_populates="location_pings")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    tourist_id = Column(Integer, ForeignKey("tourists.id"), nullable=False)
    alert_type = Column(String, nullable=False)  # area_risk, deviation, inactivity, crowd, panic
    severity = Column(String, default="medium")  # low, medium, high, critical
    message = Column(Text, nullable=False)
    lat = Column(Float)
    lng = Column(Float)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)
