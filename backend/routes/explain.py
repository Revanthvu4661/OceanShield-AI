from __future__ import annotations

from typing import Any

import pandas as pd
import shap
from fastapi import APIRouter, HTTPException

from feature_engine import engineer_single
from predictor import get_model, get_preprocessor
from routes.predict import PREDICTION_HISTORY, PREDICTION_INDEX
from schemas import ExplainResponse, HistoryItem, OceanInput, PredictionFactor


router = APIRouter()


@router.get("/explain/{prediction_id}", response_model=ExplainResponse)
def explain(prediction_id: str) -> dict:
    entry = PREDICTION_INDEX.get(prediction_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Prediction not found")

    model = get_model()
    preprocessor = get_preprocessor()
    payload = OceanInput.model_validate(entry["input"])
    engineered = engineer_single(payload)
    transformed = preprocessor.transform(pd.DataFrame([engineered]))

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(transformed)
    if isinstance(shap_values, list):
        shap_values = shap_values[1]
    row = shap_values[0]

    contributions = []
    for feature, contribution in sorted(zip(transformed.columns, row), key=lambda item: abs(item[1]), reverse=True)[:10]:
        value = engineered.get(feature, transformed.iloc[0][feature])
        direction = "increases risk" if contribution >= 0 else "reduces risk"
        contributions.append(
            PredictionFactor(
                feature=feature,
                value=value,
                contribution=float(contribution),
                direction=direction,
            )
        )

    top = contributions[:3]
    interpretation = (
        f"{entry['risk_level']} driven by "
        f"{top[0].feature} ({top[0].value}), "
        f"{top[1].feature} ({top[1].value}), and "
        f"{top[2].feature} ({top[2].value})."
        if len(top) >= 3
        else f"{entry['risk_level']} conditions detected."
    )

    return {
        "prediction_id": prediction_id,
        "risk_score": round(entry["risk_score"], 2),
        "risk_level": entry["risk_level"],
        "feature_contributions": contributions,
        "interpretation": interpretation,
    }


@router.get("/history", response_model=list[HistoryItem])
def history() -> list[dict]:
    items = []
    for item in list(PREDICTION_HISTORY)[-20:][::-1]:
        top_factor = item["top_factors"][0]["feature"] if item["top_factors"] else "unknown"
        items.append(
            {
                "prediction_id": item["prediction_id"],
                "timestamp": item["timestamp"],
                "risk_score": round(item["risk_score"], 2),
                "risk_level": item["risk_level"],
                "risk_label": item["risk_label"],
                "latitude": item["latitude"],
                "longitude": item["longitude"],
                "top_factor": top_factor,
            }
        )
    return items

