from __future__ import annotations

from fastapi import APIRouter

from background_jobs import background_status
from schemas import BackgroundAnomalyItem, BackgroundStatusResponse


router = APIRouter()


@router.get("/background/status", response_model=BackgroundStatusResponse)
def get_background_status() -> dict:
    return background_status()


@router.get("/background/anomalies", response_model=list[BackgroundAnomalyItem])
def get_background_anomalies() -> list[dict]:
    return background_status()["recent_anomalies"]
