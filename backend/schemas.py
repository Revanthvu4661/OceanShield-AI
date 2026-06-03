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
    dewpoint: float
    windgust: float
    sigheight: float
    swellheight: float
    swelldir: float
    period: float
    watertemp: float
    moon_illumination: float = 50.0
    moon_phase: str = "Full Moon"
    maxtemp: float
    mintemp: float
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


class AISearchRequest(BaseModel):
    query: str = Field(..., min_length=3)
    gemini_api_key: str = Field(..., min_length=10)


class AISearchResponse(BaseModel):
    answer: str
    key_points: list[str]
    risk_factors: list[str]
    sources_note: str
    query: str

