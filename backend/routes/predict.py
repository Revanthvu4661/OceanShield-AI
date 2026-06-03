from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from uuid import uuid4

import pandas as pd
from fastapi import APIRouter

from feature_engine import engineer_single
from predictor import get_metadata, get_model, get_preprocessor
from schemas import OceanInput, PredictionFactor, PredictionResponse


router = APIRouter()
PREDICTION_HISTORY: deque[dict] = deque(maxlen=50)
PREDICTION_INDEX: dict[str, dict] = {}


def _risk_level_from_score(score: float) -> str:
    if score <= 30:
        return "SAFE"
    if score <= 65:
        return "ELEVATED"
    return "HIGH RISK"


def _build_top_factors(engineered: dict, metadata: dict) -> list[PredictionFactor]:
    factors = []
    for item in metadata.get("top_shap_features", [])[:3]:
        feature = item["feature"]
        value = engineered.get(feature)
        factors.append(
            PredictionFactor(
                feature=feature,
                value=value,
                importance=float(item.get("mean_abs_shap", 0.0)),
            )
        )
    return factors


@router.post("/predict", response_model=PredictionResponse)
def predict(payload: OceanInput) -> dict:
    model = get_model()
    metadata = get_metadata()
    preprocessor = get_preprocessor()

    engineered = engineer_single(payload)
    frame = pd.DataFrame([engineered])
    transformed = preprocessor.transform(frame)

    probability = float(model.predict_proba(transformed)[:, 1][0])
    risk_score = probability * 100.0
    risk_label = int(probability >= 0.5)
    risk_level = _risk_level_from_score(risk_score)
    prediction_id = str(uuid4())
    top_factors = _build_top_factors(engineered, metadata)
    timestamp = datetime.now(timezone.utc).isoformat()

    record = {
        "prediction_id": prediction_id,
        "timestamp": timestamp,
        "input": payload.model_dump(),
        "engineered": engineered,
        "risk_score": risk_score,
        "risk_label": risk_label,
        "risk_level": risk_level,
        "probability": probability,
        "top_factors": [factor.model_dump() for factor in top_factors],
        "latitude": payload.latitude,
        "longitude": payload.longitude,
    }
    PREDICTION_HISTORY.append(record)
    PREDICTION_INDEX[prediction_id] = record

    return {
        "risk_score": round(risk_score, 2),
        "risk_label": risk_label,
        "risk_level": risk_level,
        "probability": probability,
        "top_factors": top_factors,
        "prediction_id": prediction_id,
        "latitude": payload.latitude,
        "longitude": payload.longitude,
    }

