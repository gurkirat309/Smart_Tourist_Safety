from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.services.websocket_manager import manager

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/police")
async def police_ws(websocket: WebSocket):
    """Police dashboard WebSocket – receives all location updates and alerts."""
    await manager.connect_police(websocket)
    try:
        while True:
            # Keep connection alive; we only push, not receive police messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_police(websocket)


@router.websocket("/tourist/{tourist_id}")
async def tourist_ws(websocket: WebSocket, tourist_id: int):
    """Individual tourist WebSocket – receives personal risk updates and alerts."""
    await manager.connect_tourist(websocket, tourist_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_tourist(websocket, tourist_id)
