from __future__ import annotations

from fastapi import APIRouter

from predictor import get_metadata
from schemas import ModelMetaResponse


router = APIRouter()


@router.get("/model-meta", response_model=ModelMetaResponse)
def model_meta() -> dict:
    metadata = get_metadata()
    metrics = metadata["performance_metrics"]
    confusion = metadata["confusion_matrix"]
    return {
        "accuracy": metrics["accuracy"],
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "f1": metrics["f1"],
        "roc_auc": metrics["roc_auc"],
        "tp": confusion["tp"],
        "fp": confusion["fp"],
        "fn": confusion["fn"],
        "tn": confusion["tn"],
    }
