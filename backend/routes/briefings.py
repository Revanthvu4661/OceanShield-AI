from __future__ import annotations

from fastapi import APIRouter, HTTPException

from schemas import DailyBriefingItem
from storage import (
    get_daily_briefing_by_date,
    get_latest_daily_briefing,
    list_daily_briefings,
)


router = APIRouter()


@router.get("/briefings/latest", response_model=DailyBriefingItem | None)
def get_latest_briefing() -> dict | None:
    return get_latest_daily_briefing()


@router.get("/briefings/history", response_model=list[DailyBriefingItem])
def get_briefing_history() -> list[dict]:
    return list_daily_briefings(10)


@router.get("/briefings/{briefing_date}", response_model=DailyBriefingItem)
def get_briefing_by_date(briefing_date: str) -> dict:
    briefing = get_daily_briefing_by_date(briefing_date)
    if not briefing:
        raise HTTPException(status_code=404, detail="Briefing not found")
    return briefing
