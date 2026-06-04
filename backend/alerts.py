from __future__ import annotations

import asyncio
from collections import deque
from queue import Empty, SimpleQueue
from typing import Any

from fastapi import WebSocket


_pending_alerts: SimpleQueue[dict[str, Any]] = SimpleQueue()
_recent_alerts: deque[dict[str, Any]] = deque(maxlen=50)
_connected_clients: set[WebSocket] = set()


def queue_alert(alert: dict[str, Any]) -> None:
    _pending_alerts.put(alert)


async def _broadcast(alert: dict[str, Any]) -> None:
    stale_clients: list[WebSocket] = []
    for websocket in list(_connected_clients):
        try:
            await websocket.send_json(alert)
        except Exception:
            stale_clients.append(websocket)
    for websocket in stale_clients:
        _connected_clients.discard(websocket)


async def alert_dispatcher_loop(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        drained = False
        while True:
            try:
                alert = _pending_alerts.get_nowait()
            except Empty:
                break
            drained = True
            _recent_alerts.appendleft(alert)
            await _broadcast(alert)
        if not drained:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                pass


async def register_alert_client(websocket: WebSocket) -> None:
    await websocket.accept()
    _connected_clients.add(websocket)
    for alert in list(_recent_alerts)[:5]:
        await websocket.send_json(alert)


def unregister_alert_client(websocket: WebSocket) -> None:
    _connected_clients.discard(websocket)


def get_recent_alerts(limit: int = 20) -> list[dict[str, Any]]:
    return list(_recent_alerts)[:limit]
