"""
WebSocket Connection Manager & Live Broadcaster
================================================
Manages connected clients and broadcasts alert / tracking events
to the Police Dashboard and individual Tourist Portals.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Set

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # police_sockets: all police dashboard connections
        self.police_sockets: Set[WebSocket] = set()
        # tourist_sockets: tourist_id → list of websockets
        self.tourist_sockets: Dict[int, List[WebSocket]] = {}

    # ── Connection lifecycle ──────────────────────────────────────────────────

    async def connect_police(self, ws: WebSocket):
        await ws.accept()
        self.police_sockets.add(ws)

    def disconnect_police(self, ws: WebSocket):
        self.police_sockets.discard(ws)

    async def connect_tourist(self, ws: WebSocket, tourist_id: int):
        await ws.accept()
        self.tourist_sockets.setdefault(tourist_id, []).append(ws)

    def disconnect_tourist(self, ws: WebSocket, tourist_id: int):
        if tourist_id in self.tourist_sockets:
            try:
                self.tourist_sockets[tourist_id].remove(ws)
            except ValueError:
                pass

    # ── Broadcast helpers ─────────────────────────────────────────────────────

    async def _send(self, ws: WebSocket, data: dict) -> bool:
        """Send JSON to a single socket; return False if connection is dead."""
        try:
            await ws.send_json(data)
            return True
        except Exception:
            return False

    async def broadcast_to_police(self, payload: dict):
        """Send a message to ALL connected police dashboards."""
        dead = set()
        for ws in self.police_sockets:
            if not await self._send(ws, payload):
                dead.add(ws)
        self.police_sockets -= dead

    async def send_to_tourist(self, tourist_id: int, payload: dict):
        """Send a message to a specific tourist's connected sockets."""
        if tourist_id not in self.tourist_sockets:
            return
        dead = []
        for ws in self.tourist_sockets[tourist_id]:
            if not await self._send(ws, payload):
                dead.append(ws)
        for ws in dead:
            self.tourist_sockets[tourist_id].remove(ws)

    # ── High-level event emitters ─────────────────────────────────────────────

    async def emit_location_update(self, tourist_id: int, name: str,
                                   lat: float, lng: float,
                                   risk_score: float, is_deviation: bool,
                                   is_inactive: bool, crowd_risk: float):
        payload = {
            "event": "location_update",
            "tourist_id": tourist_id,
            "name": name,
            "lat": lat,
            "lng": lng,
            "composite_risk_score": round(risk_score, 4),
            "is_deviation": is_deviation,
            "is_inactive": is_inactive,
            "crowd_risk": round(crowd_risk, 4),
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.broadcast_to_police(payload)
        await self.send_to_tourist(tourist_id, payload)

    async def emit_alert(self, alert_dict: dict):
        payload = {"event": "alert", **alert_dict}
        await self.broadcast_to_police(payload)
        # Also notify the affected tourist
        tourist_id = alert_dict.get("tourist_id")
        if tourist_id:
            await self.send_to_tourist(tourist_id, payload)

    async def emit_cluster_update(self, clusters: list):
        payload = {"event": "cluster_update", "clusters": clusters,
                   "timestamp": datetime.utcnow().isoformat()}
        await self.broadcast_to_police(payload)


# Singleton instance shared across routes
manager = ConnectionManager()
