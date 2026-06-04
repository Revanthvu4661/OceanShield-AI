from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from agent import get_current_conditions
from alerts import queue_alert
from feature_engine import PRESSURE_MEAN
from prediction_service import predict_ocean_state
from schemas import OceanInput
from settings import (
    BACKGROUND_POLL_INTERVAL_SECONDS,
    DAILY_BRIEFING_UTC_HOUR,
    DEFAULT_GEMINI_MODEL,
    GEMINI_API_KEY,
)
from storage import (
    get_daily_briefing_by_date,
    get_recent_station_snapshots,
    get_latest_background_run,
    get_latest_daily_briefing,
    initialize_background_store,
    get_latest_alert_event,
    list_background_snapshots,
    list_background_anomalies,
    list_daily_briefings,
    list_alert_events,
    new_run_id,
    save_alert_event,
    save_background_anomaly,
    save_daily_briefing,
    save_background_run,
    save_background_snapshot,
)


MONITORED_STATIONS: list[dict[str, Any]] = [
    {"source": "NOAA NDBC", "station_name": "Mumbai Corridor", "latitude": 18.94, "longitude": 72.84, "idbeach": "2001"},
    {"source": "NOAA NDBC", "station_name": "Arabian Sea West", "latitude": 14.50, "longitude": 58.00, "idbeach": "2002"},
    {"source": "NOAA NDBC", "station_name": "Aden Approach", "latitude": 12.78, "longitude": 45.02, "idbeach": "2003"},
    {"source": "Copernicus", "station_name": "Oman Channel", "latitude": 21.20, "longitude": 59.50, "idbeach": "3001"},
    {"source": "Copernicus", "station_name": "Sri Lanka South", "latitude": 6.90, "longitude": 80.90, "idbeach": "3002"},
    {"source": "Copernicus", "station_name": "Somali Basin", "latitude": 3.00, "longitude": 53.00, "idbeach": "3003"},
]

HIGH_RISK_THRESHOLD = 65.0
FOCUS_LAT_RANGE = (-45.0, 35.0)
FOCUS_LON_RANGE = (20.0, 120.0)


def _serializable_risk(risk: dict[str, Any]) -> dict[str, Any]:
    serializable = dict(risk)
    serializable["top_factors"] = [
        item.model_dump() if hasattr(item, "model_dump") else dict(item)
        for item in risk.get("top_factors", [])
    ]
    return serializable


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _utc_date_key(dt: datetime | None = None) -> str:
    return (dt or _now_utc()).date().isoformat()


def _wave_severity_from_payload(payload: OceanInput) -> float:
    period_norm = payload.period / 8.0
    gust_norm = payload.windgust / 20.0
    return round(
        0.40 * payload.sigheight
        + 0.25 * payload.swellheight
        + 0.20 * period_norm
        + 0.15 * gust_norm,
        4,
    )


def _severity_label(delta: float, magnitude: float, threshold: float) -> str:
    if delta <= -threshold or magnitude >= threshold * 1.8:
        return "HIGH"
    if delta <= -threshold * 0.7 or magnitude >= threshold * 1.2:
        return "MEDIUM"
    return "LOW"


def _detect_station_anomalies(
    run_id: str,
    snapshot_id: int,
    payload: OceanInput,
    station_name: str,
    risk: dict[str, Any],
) -> list[dict[str, Any]]:
    recent = get_recent_station_snapshots(station_name, limit=5)
    previous_conditions = [item["conditions"] for item in recent[1:]]

    if previous_conditions:
        baseline_pressure = sum(item["pressure"] for item in previous_conditions) / len(previous_conditions)
        baseline_wave_severity = sum(_wave_severity_from_payload(OceanInput.model_validate(item)) for item in previous_conditions) / len(previous_conditions)
    else:
        baseline_pressure = PRESSURE_MEAN
        baseline_wave_severity = _wave_severity_from_payload(payload)

    current_wave_severity = _wave_severity_from_payload(payload)
    pressure_delta = float(payload.pressure - baseline_pressure)
    wave_delta = float(current_wave_severity - baseline_wave_severity)

    anomalies: list[dict[str, Any]] = []

    if pressure_delta <= -4.0:
        severity = _severity_label(pressure_delta, abs(pressure_delta), 4.0)
        anomaly_id = save_background_anomaly(
            run_id=run_id,
            snapshot_id=snapshot_id,
            station_name=station_name,
            anomaly_type="pressure_drop",
            severity=severity,
            baseline_value=round(baseline_pressure, 2),
            current_value=round(payload.pressure, 2),
            delta=round(pressure_delta, 2),
            rule="pressure_delta <= -4 hPa vs recent station baseline",
            details={
                "baseline_pressure": round(baseline_pressure, 2),
                "current_pressure": payload.pressure,
                "pressure_anomaly": round(payload.pressure - PRESSURE_MEAN, 2),
                "risk_score": risk["risk_score"],
            },
        )
        anomalies.append(
            {
                "anomaly_id": anomaly_id,
                "anomaly_type": "pressure_drop",
                "severity": severity,
                "baseline_value": round(baseline_pressure, 2),
                "current_value": round(payload.pressure, 2),
                "delta": round(pressure_delta, 2),
            }
        )

    if wave_delta >= 0.65:
        severity = _severity_label(wave_delta, wave_delta, 0.65)
        anomaly_id = save_background_anomaly(
            run_id=run_id,
            snapshot_id=snapshot_id,
            station_name=station_name,
            anomaly_type="wave_severity_spike",
            severity=severity,
            baseline_value=round(baseline_wave_severity, 4),
            current_value=round(current_wave_severity, 4),
            delta=round(wave_delta, 4),
            rule="wave_severity increase >= 0.65 vs recent station baseline",
            details={
                "baseline_wave_severity": round(baseline_wave_severity, 4),
                "current_wave_severity": round(current_wave_severity, 4),
                "sigheight": payload.sigheight,
                "swellheight": payload.swellheight,
                "period": payload.period,
                "risk_score": risk["risk_score"],
            },
        )
        anomalies.append(
            {
                "anomaly_id": anomaly_id,
                "anomaly_type": "wave_severity_spike",
                "severity": severity,
                "baseline_value": round(baseline_wave_severity, 4),
                "current_value": round(current_wave_severity, 4),
                "delta": round(wave_delta, 4),
            }
        )

    return anomalies


def _build_payload(station: dict[str, Any], collected_hour: int) -> OceanInput:
    conditions = get_current_conditions(station["latitude"], station["longitude"], reference_hour=collected_hour)
    merged = {
        **conditions,
        "idbeach": station["idbeach"],
        "latitude": station["latitude"],
        "longitude": station["longitude"],
        "conditions_source": station["source"],
        "station_name": station["station_name"],
    }
    return OceanInput.model_validate(merged)


def _in_focus_region(latitude: float, longitude: float) -> bool:
    return FOCUS_LAT_RANGE[0] <= latitude <= FOCUS_LAT_RANGE[1] and FOCUS_LON_RANGE[0] <= longitude <= FOCUS_LON_RANGE[1]


def _queue_high_risk_alert(
    run_id: str,
    snapshot_id: int,
    station: dict[str, Any],
    payload: OceanInput,
    risk: dict[str, Any],
) -> dict[str, Any] | None:
    recent = get_recent_station_snapshots(station["station_name"], limit=2)
    previous_risk = recent[1]["risk"] if len(recent) > 1 else None
    if risk.get("risk_level") != "HIGH RISK":
        return None
    if previous_risk and previous_risk.get("risk_level") == "HIGH RISK":
        return None

    message = (
        f"{station['station_name']} has transitioned into HIGH RISK with a risk score of "
        f"{risk['risk_score']:.2f}."
    )
    alert_payload = {
        "run_id": run_id,
        "snapshot_id": snapshot_id,
        "event_type": "high_risk_transition",
        "station_name": station["station_name"],
        "source": station["source"],
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "risk_score": risk["risk_score"],
        "risk_level": risk["risk_level"],
        "probability": risk["probability"],
        "top_factor": risk["top_factors"][0].feature if risk.get("top_factors") else "unknown",
        "previous_risk_level": previous_risk.get("risk_level") if previous_risk else None,
        "previous_risk_score": previous_risk.get("risk_score") if previous_risk else None,
    }
    alert_id = save_alert_event(
        event_type="high_risk_transition",
        station_name=station["station_name"],
        source=station["source"],
        latitude=payload.latitude,
        longitude=payload.longitude,
        severity="HIGH",
        message=message,
        payload=alert_payload,
    )
    alert = {
        "alert_id": alert_id,
        "event_type": "high_risk_transition",
        "created_at": _now_utc().isoformat(),
        "station_name": station["station_name"],
        "source": station["source"],
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "severity": "HIGH",
        "message": message,
        "payload": alert_payload,
    }
    queue_alert(alert)
    return alert


def _collect_briefing_raw_data() -> dict[str, Any]:
    snapshots = list_background_snapshots(250)
    anomalies = list_background_anomalies(100)
    focus_snapshots = [
        snapshot
        for snapshot in snapshots
        if _in_focus_region(snapshot["latitude"], snapshot["longitude"]) and snapshot["risk_score"] >= HIGH_RISK_THRESHOLD
    ]
    if not focus_snapshots:
        focus_snapshots = [
            snapshot
            for snapshot in snapshots
            if _in_focus_region(snapshot["latitude"], snapshot["longitude"])
        ][:20]

    focus_stations = sorted({item["station_name"] for item in focus_snapshots})
    related_anomalies = [anomaly for anomaly in anomalies if anomaly["station_name"] in focus_stations]
    high_risk_zones = [
        {
            "station_name": item["station_name"],
            "source": item["source"],
            "latitude": item["latitude"],
            "longitude": item["longitude"],
            "risk_score": item["risk_score"],
            "risk_level": item["risk_level"],
            "probability": item["probability"],
            "top_factor": item["top_factor"],
            "collected_at": item["collected_at"],
        }
        for item in focus_snapshots[:12]
    ]
    return {
        "generated_at": _now_utc().isoformat(),
        "focus_region": {
            "latitude_range": FOCUS_LAT_RANGE,
            "longitude_range": FOCUS_LON_RANGE,
        },
        "high_risk_zones": high_risk_zones,
        "anomaly_highlights": related_anomalies[:15],
        "high_risk_count": len(high_risk_zones),
        "anomaly_count": len(related_anomalies),
    }


def _build_briefing_prompt(raw_data: dict[str, Any]) -> str:
    return (
        "You are writing the OceanShield Daily Maritime Safety Briefing for operators covering the Indian Ocean "
        "and Arabian Sea. Turn the raw risk data into a polished plain-English operational briefing.\n\n"
        "Requirements:\n"
        "- Title the briefing.\n"
        "- Start with a 2-3 sentence executive summary.\n"
        "- Include bullet points for the top risk zones.\n"
        "- Mention any notable anomalies or pressure drops.\n"
        "- Add a short precautions section.\n"
        "- Keep the language clear, concise, and ready to distribute.\n"
        "- Output markdown only.\n\n"
        f"Raw data JSON:\n{json.dumps(raw_data, indent=2, default=str)}"
    )


def _fallback_briefing(raw_data: dict[str, Any]) -> dict[str, Any]:
    zones = raw_data.get("high_risk_zones", [])
    anomalies = raw_data.get("anomaly_highlights", [])
    title = "Daily Maritime Safety Briefing"
    lead = (
        f"{len(zones)} elevated zones were identified across the Indian Ocean / Arabian Sea focus region. "
        f"The highest risk areas are concentrated around {zones[0]['station_name'] if zones else 'the monitored lanes'}."
    )
    bullets = []
    for zone in zones[:5]:
        bullets.append(
            f"- {zone['station_name']}: risk {zone['risk_score']:.2f} ({zone['risk_level']}), top factor {zone['top_factor']}"
        )
    if anomalies:
        bullets.append(f"- Notable anomalies: {len(anomalies)} flagged pressure or wave-severity events in the latest sweep.")
    body = "\n".join(
        [
            f"# {title}",
            "",
            lead,
            "",
            "## Top Risk Zones",
            *bullets,
            "",
            "## Precautions",
            "- Delay non-essential transits through the most exposed lanes.",
            "- Watch for rapid pressure drops and rising wave severity.",
            "- Re-check conditions before route commitments.",
        ]
    )
    return {"title": title, "briefing_text": body}


def _generate_briefing_text(raw_data: dict[str, Any]) -> tuple[str, str]:
    try:
        from google import genai
    except ImportError:
        fallback = _fallback_briefing(raw_data)
        return fallback["title"], fallback["briefing_text"]

    if not GEMINI_API_KEY:
        fallback = _fallback_briefing(raw_data)
        return fallback["title"], fallback["briefing_text"]

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=DEFAULT_GEMINI_MODEL,
            contents=_build_briefing_prompt(raw_data),
            config={
                "temperature": 0.25,
                "max_output_tokens": 900,
            },
        )
        text = (getattr(response, "text", None) or "").strip()
        if not text:
            raise RuntimeError("Gemini returned an empty briefing")
        first_line = text.splitlines()[0].lstrip("# ").strip() if text.splitlines() else "Daily Maritime Safety Briefing"
        return first_line or "Daily Maritime Safety Briefing", text
    except Exception:
        fallback = _fallback_briefing(raw_data)
        return fallback["title"], fallback["briefing_text"]


def generate_daily_maritime_briefing(trigger_source: str = "cron") -> dict[str, Any]:
    initialize_background_store()
    raw_data = _collect_briefing_raw_data()
    briefing_date = _utc_date_key()
    title, briefing_text = _generate_briefing_text(raw_data)
    model_name = DEFAULT_GEMINI_MODEL if GEMINI_API_KEY else "fallback"
    save_daily_briefing(
        briefing_date=briefing_date,
        trigger_source=trigger_source,
        model_name=model_name,
        status="completed",
        title=title,
        briefing_text=briefing_text,
        raw=raw_data,
    )
    return {
        "briefing_date": briefing_date,
        "title": title,
        "briefing_text": briefing_text,
        "raw": raw_data,
    }


def _seconds_until_utc_hour(target_hour: int) -> float:
    now = _now_utc()
    next_run = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
    if now >= next_run:
        next_run = next_run + timedelta(days=1)
    return max(1.0, (next_run - now).total_seconds())


async def daily_briefing_loop(stop_event: asyncio.Event) -> None:
    initialize_background_store()
    briefing_date = _utc_date_key()
    if _now_utc().hour >= DAILY_BRIEFING_UTC_HOUR and not get_daily_briefing_by_date(briefing_date):
        await asyncio.to_thread(generate_daily_maritime_briefing, "startup_catchup")

    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=_seconds_until_utc_hour(DAILY_BRIEFING_UTC_HOUR))
        except asyncio.TimeoutError:
            await asyncio.to_thread(generate_daily_maritime_briefing, "cron")


def run_background_sweep(trigger_source: str = "scheduler") -> dict[str, Any]:
    initialize_background_store()
    run_id = new_run_id()
    now = datetime.now(timezone.utc)
    collected_hour = now.hour
    snapshots: list[dict[str, Any]] = []
    anomalies: list[dict[str, Any]] = []
    alerts: list[dict[str, Any]] = []

    for station in MONITORED_STATIONS:
        payload = _build_payload(station, collected_hour)
        risk = _serializable_risk(predict_ocean_state(payload))
        snapshot_id = save_background_snapshot(
            run_id=run_id,
            source=station["source"],
            station_name=station["station_name"],
            latitude=payload.latitude,
            longitude=payload.longitude,
            conditions=payload.model_dump(),
            risk=risk,
        )
        snapshots.append(
            {
                "snapshot_id": snapshot_id,
                "source": station["source"],
                "station_name": station["station_name"],
                "latitude": payload.latitude,
                "longitude": payload.longitude,
                "risk_score": risk["risk_score"],
                "risk_level": risk["risk_level"],
                "probability": risk["probability"],
                "top_factor": risk["top_factors"][0].feature if risk["top_factors"] else "unknown",
            }
        )
        anomalies.extend(_detect_station_anomalies(run_id, snapshot_id, payload, station["station_name"], risk))
        alert = _queue_high_risk_alert(run_id, snapshot_id, station, payload, risk)
        if alert is not None:
            alerts.append(alert)

    high_risk_count = sum(1 for snapshot in snapshots if snapshot["risk_level"] == "HIGH RISK")
    average_risk_score = round(sum(snapshot["risk_score"] for snapshot in snapshots) / len(snapshots), 2)
    summary = {
        "run_id": run_id,
        "trigger_source": trigger_source,
        "collected_at": now.isoformat(),
        "snapshot_count": len(snapshots),
        "high_risk_count": high_risk_count,
        "anomaly_count": len(anomalies),
        "average_risk_score": average_risk_score,
        "latest_snapshot": snapshots[-1] if snapshots else None,
        "interval_seconds": BACKGROUND_POLL_INTERVAL_SECONDS,
        "anomalies": anomalies[:10],
        "alerts": alerts[:10],
        "alert_count": len(alerts),
    }
    save_background_run(run_id=run_id, trigger_source=trigger_source, status="completed", summary=summary)
    return summary


async def background_loop(stop_event: asyncio.Event) -> None:
    initialize_background_store()
    await asyncio.to_thread(run_background_sweep, "startup")
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=BACKGROUND_POLL_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            await asyncio.to_thread(run_background_sweep, "scheduled")


def background_status() -> dict[str, Any]:
    initialize_background_store()
    latest_run = get_latest_background_run()
    return {
        "latest_run": latest_run,
        "recent_snapshots": list_background_snapshots(12),
        "recent_anomalies": list_background_anomalies(20),
        "latest_briefing": get_latest_daily_briefing(),
        "recent_briefings": list_daily_briefings(5),
        "latest_alert": get_latest_alert_event(),
        "recent_alerts": list_alert_events(10),
    }
