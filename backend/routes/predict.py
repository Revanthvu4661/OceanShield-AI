from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter

from prediction_service import predict_ocean_state
from schemas import OceanInput, PredictionResponse


router = APIRouter()
PREDICTION_HISTORY: deque[dict] = deque(maxlen=50)
PREDICTION_INDEX: dict[str, dict] = {}

@router.post("/predict", response_model=PredictionResponse)
def predict(payload: OceanInput) -> dict:
    result = predict_ocean_state(payload)
    prediction_id = str(uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    record = {
        "prediction_id": prediction_id,
        "timestamp": timestamp,
        "input": payload.model_dump(),
        "engineered": result["engineered"],
        "risk_score": result["risk_score"],
        "risk_label": result["risk_label"],
        "risk_level": result["risk_level"],
        "probability": result["probability"],
        "top_factors": [factor.model_dump() for factor in result["top_factors"]],
        "latitude": payload.latitude,
        "longitude": payload.longitude,
    }
    PREDICTION_HISTORY.append(record)
    PREDICTION_INDEX[prediction_id] = record

    return {
        "risk_score": result["risk_score"],
        "risk_label": result["risk_label"],
        "risk_level": result["risk_level"],
        "probability": result["probability"],
        "top_factors": result["top_factors"],
        "prediction_id": prediction_id,
        "latitude": payload.latitude,
        "longitude": payload.longitude,
    }
