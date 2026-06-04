from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator
from uuid import uuid4

from settings import BACKGROUND_DB_PATH, BACKEND_RUNTIME_DIR


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    BACKEND_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(BACKGROUND_DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


@contextmanager
def db_session() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def initialize_background_store() -> None:
    with db_session() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS background_runs (
                run_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                trigger_source TEXT NOT NULL,
                status TEXT NOT NULL,
                summary_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS background_snapshots (
                snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                collected_at TEXT NOT NULL,
                source TEXT NOT NULL,
                station_name TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                conditions_json TEXT NOT NULL,
                risk_json TEXT NOT NULL,
                FOREIGN KEY(run_id) REFERENCES background_runs(run_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS background_anomalies (
                anomaly_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                snapshot_id INTEGER NOT NULL,
                detected_at TEXT NOT NULL,
                station_name TEXT NOT NULL,
                anomaly_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                baseline_value REAL NOT NULL,
                current_value REAL NOT NULL,
                delta REAL NOT NULL,
                rule TEXT NOT NULL,
                details_json TEXT NOT NULL,
                FOREIGN KEY(run_id) REFERENCES background_runs(run_id),
                FOREIGN KEY(snapshot_id) REFERENCES background_snapshots(snapshot_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_briefings (
                briefing_id INTEGER PRIMARY KEY AUTOINCREMENT,
                briefing_date TEXT NOT NULL UNIQUE,
                generated_at TEXT NOT NULL,
                trigger_source TEXT NOT NULL,
                model_name TEXT NOT NULL,
                status TEXT NOT NULL,
                title TEXT NOT NULL,
                briefing_text TEXT NOT NULL,
                raw_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS alert_events (
                alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                station_name TEXT NOT NULL,
                source TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )


def save_background_run(run_id: str, trigger_source: str, status: str, summary: dict[str, Any]) -> None:
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO background_runs(run_id, created_at, trigger_source, status, summary_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                status=excluded.status,
                summary_json=excluded.summary_json
            """,
            (run_id, _utc_now(), trigger_source, status, json.dumps(summary, default=str)),
        )


def save_background_snapshot(
    run_id: str,
    source: str,
    station_name: str,
    latitude: float,
    longitude: float,
    conditions: dict[str, Any],
    risk: dict[str, Any],
) -> int:
    with db_session() as conn:
        cursor = conn.execute(
            """
            INSERT INTO background_snapshots(
                run_id, collected_at, source, station_name, latitude, longitude, conditions_json, risk_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                _utc_now(),
                source,
                station_name,
                latitude,
                longitude,
                json.dumps(conditions, default=str),
                json.dumps(risk, default=str),
            ),
        )
        return int(cursor.lastrowid)


def get_recent_station_snapshots(station_name: str, limit: int = 5) -> list[dict[str, Any]]:
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT snapshot_id, run_id, collected_at, source, station_name, latitude, longitude,
                   conditions_json, risk_json
            FROM background_snapshots
            WHERE station_name = ?
            ORDER BY snapshot_id DESC
            LIMIT ?
            """,
            (station_name, limit),
        ).fetchall()

    snapshots: list[dict[str, Any]] = []
    for row in rows:
        conditions = json.loads(row["conditions_json"])
        risk = json.loads(row["risk_json"])
        snapshots.append(
            {
                "snapshot_id": row["snapshot_id"],
                "run_id": row["run_id"],
                "collected_at": row["collected_at"],
                "source": row["source"],
                "station_name": row["station_name"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "conditions": conditions,
                "risk": risk,
            }
        )
    return snapshots


def save_background_anomaly(
    run_id: str,
    snapshot_id: int,
    station_name: str,
    anomaly_type: str,
    severity: str,
    baseline_value: float,
    current_value: float,
    delta: float,
    rule: str,
    details: dict[str, Any],
) -> int:
    with db_session() as conn:
        cursor = conn.execute(
            """
            INSERT INTO background_anomalies(
                run_id, snapshot_id, detected_at, station_name, anomaly_type, severity,
                baseline_value, current_value, delta, rule, details_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                snapshot_id,
                _utc_now(),
                station_name,
                anomaly_type,
                severity,
                baseline_value,
                current_value,
                delta,
                rule,
                json.dumps(details, default=str),
            ),
        )
        return int(cursor.lastrowid)


def list_background_anomalies(limit: int = 50) -> list[dict[str, Any]]:
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT anomaly_id, run_id, snapshot_id, detected_at, station_name, anomaly_type, severity,
                   baseline_value, current_value, delta, rule, details_json
            FROM background_anomalies
            ORDER BY anomaly_id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    anomalies: list[dict[str, Any]] = []
    for row in rows:
        anomalies.append(
            {
                "anomaly_id": row["anomaly_id"],
                "run_id": row["run_id"],
                "snapshot_id": row["snapshot_id"],
                "detected_at": row["detected_at"],
                "station_name": row["station_name"],
                "anomaly_type": row["anomaly_type"],
                "severity": row["severity"],
                "baseline_value": float(row["baseline_value"]),
                "current_value": float(row["current_value"]),
                "delta": float(row["delta"]),
                "rule": row["rule"],
                "details": json.loads(row["details_json"]),
            }
        )
    return anomalies


def list_background_snapshots(limit: int = 25) -> list[dict[str, Any]]:
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT snapshot_id, run_id, collected_at, source, station_name, latitude, longitude,
                   conditions_json, risk_json
            FROM background_snapshots
            ORDER BY snapshot_id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    snapshots: list[dict[str, Any]] = []
    for row in rows:
        conditions = json.loads(row["conditions_json"])
        risk = json.loads(row["risk_json"])
        snapshots.append(
            {
                "snapshot_id": row["snapshot_id"],
                "run_id": row["run_id"],
                "collected_at": row["collected_at"],
                "source": row["source"],
                "station_name": row["station_name"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "risk_score": float(risk["risk_score"]),
                "risk_level": risk["risk_level"],
                "probability": float(risk["probability"]),
                "top_factor": risk.get("top_factors", [{}])[0].get("feature", "unknown"),
                "conditions": conditions,
                "risk": risk,
            }
        )
    return snapshots


def get_latest_daily_briefing() -> dict[str, Any] | None:
    with db_session() as conn:
        row = conn.execute(
            """
            SELECT briefing_id, briefing_date, generated_at, trigger_source, model_name, status,
                   title, briefing_text, raw_json
            FROM daily_briefings
            ORDER BY briefing_date DESC, briefing_id DESC
            LIMIT 1
            """
        ).fetchone()
    if not row:
        return None
    return {
        "briefing_id": row["briefing_id"],
        "briefing_date": row["briefing_date"],
        "generated_at": row["generated_at"],
        "trigger_source": row["trigger_source"],
        "model_name": row["model_name"],
        "status": row["status"],
        "title": row["title"],
        "briefing_text": row["briefing_text"],
        "raw": json.loads(row["raw_json"]),
    }


def list_daily_briefings(limit: int = 10) -> list[dict[str, Any]]:
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT briefing_id, briefing_date, generated_at, trigger_source, model_name, status,
                   title, briefing_text, raw_json
            FROM daily_briefings
            ORDER BY briefing_date DESC, briefing_id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    briefings: list[dict[str, Any]] = []
    for row in rows:
        briefings.append(
            {
                "briefing_id": row["briefing_id"],
                "briefing_date": row["briefing_date"],
                "generated_at": row["generated_at"],
                "trigger_source": row["trigger_source"],
                "model_name": row["model_name"],
                "status": row["status"],
                "title": row["title"],
                "briefing_text": row["briefing_text"],
                "raw": json.loads(row["raw_json"]),
            }
        )
    return briefings


def get_daily_briefing_by_date(briefing_date: str) -> dict[str, Any] | None:
    with db_session() as conn:
        row = conn.execute(
            """
            SELECT briefing_id, briefing_date, generated_at, trigger_source, model_name, status,
                   title, briefing_text, raw_json
            FROM daily_briefings
            WHERE briefing_date = ?
            LIMIT 1
            """,
            (briefing_date,),
        ).fetchone()
    if not row:
        return None
    return {
        "briefing_id": row["briefing_id"],
        "briefing_date": row["briefing_date"],
        "generated_at": row["generated_at"],
        "trigger_source": row["trigger_source"],
        "model_name": row["model_name"],
        "status": row["status"],
        "title": row["title"],
        "briefing_text": row["briefing_text"],
        "raw": json.loads(row["raw_json"]),
    }


def save_daily_briefing(
    briefing_date: str,
    trigger_source: str,
    model_name: str,
    status: str,
    title: str,
    briefing_text: str,
    raw: dict[str, Any],
) -> int:
    with db_session() as conn:
        cursor = conn.execute(
            """
            INSERT INTO daily_briefings(
                briefing_date, generated_at, trigger_source, model_name, status, title, briefing_text, raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(briefing_date) DO UPDATE SET
                generated_at=excluded.generated_at,
                trigger_source=excluded.trigger_source,
                model_name=excluded.model_name,
                status=excluded.status,
                title=excluded.title,
                briefing_text=excluded.briefing_text,
                raw_json=excluded.raw_json
            """,
            (
                briefing_date,
                _utc_now(),
                trigger_source,
                model_name,
                status,
                title,
                briefing_text,
                json.dumps(raw, default=str),
            ),
        )
        return int(cursor.lastrowid or 0)


def list_daily_briefing_dates(limit: int = 10) -> list[str]:
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT briefing_date
            FROM daily_briefings
            ORDER BY briefing_date DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [row["briefing_date"] for row in rows]


def save_alert_event(
    event_type: str,
    station_name: str,
    source: str,
    latitude: float,
    longitude: float,
    severity: str,
    message: str,
    payload: dict[str, Any],
) -> int:
    with db_session() as conn:
        cursor = conn.execute(
            """
            INSERT INTO alert_events(
                event_type, created_at, station_name, source, latitude, longitude, severity, message, payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_type,
                _utc_now(),
                station_name,
                source,
                latitude,
                longitude,
                severity,
                message,
                json.dumps(payload, default=str),
            ),
        )
        return int(cursor.lastrowid)


def list_alert_events(limit: int = 20) -> list[dict[str, Any]]:
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT alert_id, event_type, created_at, station_name, source, latitude, longitude, severity,
                   message, payload_json
            FROM alert_events
            ORDER BY alert_id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    alerts: list[dict[str, Any]] = []
    for row in rows:
        alerts.append(
            {
                "alert_id": row["alert_id"],
                "event_type": row["event_type"],
                "created_at": row["created_at"],
                "station_name": row["station_name"],
                "source": row["source"],
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "severity": row["severity"],
                "message": row["message"],
                "payload": json.loads(row["payload_json"]),
            }
        )
    return alerts


def get_latest_alert_event() -> dict[str, Any] | None:
    with db_session() as conn:
        row = conn.execute(
            """
            SELECT alert_id, event_type, created_at, station_name, source, latitude, longitude, severity,
                   message, payload_json
            FROM alert_events
            ORDER BY alert_id DESC
            LIMIT 1
            """
        ).fetchone()
    if not row:
        return None
    return {
        "alert_id": row["alert_id"],
        "event_type": row["event_type"],
        "created_at": row["created_at"],
        "station_name": row["station_name"],
        "source": row["source"],
        "latitude": float(row["latitude"]),
        "longitude": float(row["longitude"]),
        "severity": row["severity"],
        "message": row["message"],
        "payload": json.loads(row["payload_json"]),
    }


def get_latest_background_run() -> dict[str, Any] | None:
    with db_session() as conn:
        row = conn.execute(
            """
            SELECT run_id, created_at, trigger_source, status, summary_json
            FROM background_runs
            ORDER BY created_at DESC
            LIMIT 1
            """
        ).fetchone()
    if not row:
        return None
    return {
        "run_id": row["run_id"],
        "created_at": row["created_at"],
        "trigger_source": row["trigger_source"],
        "status": row["status"],
        "summary": json.loads(row["summary_json"]),
    }


def new_run_id() -> str:
    return str(uuid4())
