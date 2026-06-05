from __future__ import annotations

from typing import Any

import pandas as pd

from feature_engine import engineer_single
from predictor import get_metadata, get_model, get_preprocessor
from schemas import OceanInput, PredictionFactor


def risk_level_from_score(score: float) -> str:
    if score < 30:
        return "SAFE"
    if score < 65:
        return "CAUTION"
    return "HIGH RISK"


def build_top_factors(engineered: dict[str, Any], metadata: dict[str, Any]) -> list[PredictionFactor]:
    factors: list[PredictionFactor] = []
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


def predict_ocean_state(payload: OceanInput) -> dict[str, Any]:
    """Run the trained XGBoost model on a validated OceanInput payload."""
    model = get_model()
    metadata = get_metadata()
    preprocessor = get_preprocessor()

    engineered = engineer_single(payload)
    frame = pd.DataFrame([engineered])
    transformed = preprocessor.transform(frame)

    probability = float(model.predict_proba(transformed)[:, 1][0])
    risk_score = probability * 100.0
    risk_label = int(probability >= 0.5)
    risk_level = risk_level_from_score(risk_score)
    top_factors = build_top_factors(engineered, metadata)

    return {
        "risk_score": round(risk_score, 2),
        "risk_label": risk_label,
        "risk_level": risk_level,
        "probability": probability,
        "top_factors": top_factors,
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "engineered": engineered,
    }
