from __future__ import annotations

from fastapi import APIRouter

from predictor import get_metadata
from schemas import HealthResponse


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> dict:
    metadata = get_metadata()
    metrics = metadata["performance_metrics"]
    return {
        "status": "ok",
        "model": metadata["best_model"],
        "accuracy": metrics["accuracy"],
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "f1": metrics["f1"],
        "roc_auc": metrics["roc_auc"],
        "pr_auc": metadata["precision_recall_auc"],
        "confusion_matrix": metadata["confusion_matrix"],
        "top_feature_importance": metadata["top_feature_importance"],
        "top_shap_features": metadata["top_shap_features"],
        "training_metadata": metadata["training_metadata"],
        "handoff_notes": metadata["handoff_notes"],
    }

