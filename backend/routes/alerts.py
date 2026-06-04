from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from alerts import get_recent_alerts, register_alert_client, unregister_alert_client
from schemas import AlertEventItem
from storage import get_latest_alert_event, list_alert_events


router = APIRouter()


@router.websocket("/alerts/ws")
async def alerts_websocket(websocket: WebSocket) -> None:
    await register_alert_client(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        unregister_alert_client(websocket)
    except Exception:
        unregister_alert_client(websocket)


@router.get("/alerts/latest", response_model=AlertEventItem | None)
def get_latest_alert() -> dict | None:
    return get_latest_alert_event()


@router.get("/alerts/history", response_model=list[AlertEventItem])
def get_alert_history() -> list[dict]:
    alerts = list_alert_events(20)
    if alerts:
        return alerts
    return get_recent_alerts(20)
