from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OceanInput(BaseModel):
    windspeed: float
    winddirdegree: float
    precipitation: float = 0.0
    humidity: float
    pressure: float = 1013.25
    cloudcover: float = 50.0
    dewpoint: float = 18.0
    windgust: float
    sigheight: float
    swellheight: float
    swelldir: float
    period: float
    watertemp: float = 24.0
    moon_illumination: float = 50.0
    moon_phase: str = "Full Moon"
    maxtemp: float = 28.0
    mintemp: float = 22.0
    tide_events: int = 4
    tide_height_mean: float = 0.5
    tide_height_max: float = 1.0
    tide_height_min: float = 0.0
    tide_height_range: float = 1.0
    high_tide_count: int = 2
    low_tide_count: int = 2
    idbeach: str = "1"
    hour: int = 12
    latitude: float = 0.0
    longitude: float = 0.0


class PredictionFactor(BaseModel):
    feature: str
    value: Any
    importance: float | None = None
    contribution: float | None = None
    direction: str | None = None


class PredictionResponse(BaseModel):
    risk_score: float
    risk_label: int
    risk_level: str
    probability: float
    top_factors: list[PredictionFactor]
    prediction_id: str
    latitude: float
    longitude: float


class ExplainResponse(BaseModel):
    prediction_id: str
    risk_score: float
    risk_level: str
    feature_contributions: list[PredictionFactor]
    interpretation: str


class HistoryItem(BaseModel):
    prediction_id: str
    timestamp: str
    risk_score: float
    risk_level: str
    risk_label: int
    latitude: float
    longitude: float
    top_factor: str


class HealthResponse(BaseModel):
    status: str
    model: str
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float
    pr_auc: float
    confusion_matrix: dict[str, int]
    top_feature_importance: list[dict[str, Any]]
    top_shap_features: list[dict[str, Any]]
    training_metadata: dict[str, Any]
    handoff_notes: list[str]


class ModelMetaResponse(BaseModel):
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float
    tp: int
    fp: int
    fn: int
    tn: int


class AISearchRequest(BaseModel):
    query: str = Field(..., min_length=3)


class RouteComparisonItem(BaseModel):
    route: str
    average_risk_score: float
    peak_risk_score: float
    high_risk_waypoints: int
    status: str


class RouteAdvice(BaseModel):
    start: str
    end: str
    risk_threshold: float
    recommended_route: str
    route_summary: str
    comparison_table: list[RouteComparisonItem]
    alternatives: list[dict[str, Any]] = Field(default_factory=list)


class AgentToolTrace(BaseModel):
    tool_name: str
    arguments: dict[str, Any]
    result: dict[str, Any]


class AISearchResponse(BaseModel):
    answer: str
    key_points: list[str]
    risk_factors: list[str]
    sources_note: str
    query: str
    tool_trace: list[AgentToolTrace] = Field(default_factory=list)
    route_request: dict[str, Any] | None = None
    route_advice: RouteAdvice | None = None


class BackgroundSnapshotItem(BaseModel):
    snapshot_id: int
    run_id: str
    collected_at: str
    source: str
    station_name: str
    latitude: float
    longitude: float
    risk_score: float
    risk_level: str
    probability: float
    top_factor: str
    conditions: dict[str, Any]
    risk: dict[str, Any]


class BackgroundRunSummary(BaseModel):
    run_id: str
    created_at: str
    trigger_source: str
    status: str
    summary: dict[str, Any]


class BackgroundAnomalyItem(BaseModel):
    anomaly_id: int
    run_id: str
    snapshot_id: int
    detected_at: str
    station_name: str
    anomaly_type: str
    severity: str
    baseline_value: float
    current_value: float
    delta: float
    rule: str
    details: dict[str, Any]


class BackgroundStatusResponse(BaseModel):
    latest_run: BackgroundRunSummary | None = None
    recent_snapshots: list[BackgroundSnapshotItem] = Field(default_factory=list)
    recent_anomalies: list[BackgroundAnomalyItem] = Field(default_factory=list)
    latest_briefing: DailyBriefingItem | None = None
    recent_briefings: list[DailyBriefingItem] = Field(default_factory=list)
    latest_alert: AlertEventItem | None = None
    recent_alerts: list[AlertEventItem] = Field(default_factory=list)


class AlertEventItem(BaseModel):
    alert_id: int
    event_type: str
    created_at: str
    station_name: str
    source: str
    latitude: float
    longitude: float
    severity: str
    message: str
    payload: dict[str, Any]


class DailyBriefingItem(BaseModel):
    briefing_id: int
    briefing_date: str
    generated_at: str
    trigger_source: str
    model_name: str
    status: str
    title: str
    briefing_text: str
    raw: dict[str, Any]


class DailyBriefingResponse(BaseModel):
    latest_briefing: DailyBriefingItem | None = None
    recent_briefings: list[DailyBriefingItem] = Field(default_factory=list)
