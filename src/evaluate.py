from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

CURRENT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = CURRENT_DIR.parent
PKG_DIR = WORKSPACE_ROOT / ".python_pkgs"
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "4")

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from sklearn.metrics import (
    accuracy_score,
    auc,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

from train import train_and_compare_models


def _to_native(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _to_native(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_native(v) for v in value]
    if isinstance(value, tuple):
        return [_to_native(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    return value


def _save_confusion_matrix(cm: np.ndarray, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(5, 4))
    image = ax.imshow(cm, cmap="Blues")
    ax.set_title("Confusion Matrix")
    ax.set_xlabel("Predicted Label")
    ax.set_ylabel("True Label")
    ax.set_xticks([0, 1], labels=["Normal", "Potential Rogue Risk"])
    ax.set_yticks([0, 1], labels=["Normal", "Potential Rogue Risk"])
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, int(cm[i, j]), ha="center", va="center", color="black", fontsize=12)
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _save_roc_curve(y_true: pd.Series, probabilities: np.ndarray, output_path: Path) -> float:
    fpr, tpr, _ = roc_curve(y_true, probabilities)
    roc_auc = auc(fpr, tpr)
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(fpr, tpr, label=f"AUC = {roc_auc:.4f}", color="#b22222", linewidth=2)
    ax.plot([0, 1], [0, 1], linestyle="--", color="#666666")
    ax.set_title("ROC Curve")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.legend(loc="lower right")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return float(roc_auc)


def _save_pr_curve(y_true: pd.Series, probabilities: np.ndarray, output_path: Path) -> float:
    precision, recall, _ = precision_recall_curve(y_true, probabilities)
    pr_auc = auc(recall, precision)
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(recall, precision, label=f"AUC = {pr_auc:.4f}", color="#287271", linewidth=2)
    ax.set_title("Precision-Recall Curve")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.legend(loc="lower left")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return float(pr_auc)


def _compute_shap_importance(model: Any, X_background: pd.DataFrame, X_explain: pd.DataFrame) -> pd.DataFrame:
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_explain)
    if isinstance(shap_values, list):
        shap_values = shap_values[1]
    importance = np.abs(shap_values).mean(axis=0)
    shap_df = pd.DataFrame(
        {
            "feature": X_explain.columns,
            "mean_abs_shap": importance,
        }
    ).sort_values("mean_abs_shap", ascending=False)
    return shap_df


def _save_shap_summary_plot(model: Any, X_explain: pd.DataFrame, output_path: Path) -> None:
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_explain)
    if isinstance(shap_values, list):
        shap_values = shap_values[1]
    plt.figure(figsize=(10, 8))
    shap.summary_plot(shap_values, X_explain, show=False, plot_type="bar", max_display=20)
    plt.title("SHAP Feature Importance")
    plt.tight_layout()
    plt.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close()


def evaluate_and_export(data_dir: str | Path) -> dict[str, Any]:
    reports_dir = WORKSPACE_ROOT / "reports" / "evaluation"
    models_dir = WORKSPACE_ROOT / "models"
    reports_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)

    training = train_and_compare_models(data_dir)
    model = training.best_model
    X_train = training.X_train
    X_test = training.X_test
    y_train = training.y_train
    y_test = training.y_test

    probabilities = model.predict_proba(X_test)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)

    cm = confusion_matrix(y_test, predictions)
    tn, fp, fn, tp = [int(v) for v in cm.ravel()]

    metrics = {
        "accuracy": float(accuracy_score(y_test, predictions)),
        "precision": float(precision_score(y_test, predictions, zero_division=0)),
        "recall": float(recall_score(y_test, predictions, zero_division=0)),
        "f1": float(f1_score(y_test, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
    }

    _save_confusion_matrix(cm, reports_dir / "confusion_matrix.png")
    roc_auc = _save_roc_curve(y_test, probabilities, reports_dir / "roc_curve.png")
    pr_auc = _save_pr_curve(y_test, probabilities, reports_dir / "precision_recall_curve.png")

    feature_importance = pd.DataFrame(
        {
            "feature": training.X_train.columns,
            "importance": model.feature_importances_,
        }
    ).sort_values("importance", ascending=False)
    feature_importance.to_csv(reports_dir / "feature_importance.csv", index=False)

    explain_rows = min(600, len(X_test))
    shap_frame = X_test.sample(explain_rows, random_state=42).reset_index(drop=True)
    shap_importance = _compute_shap_importance(model, X_train, shap_frame)
    shap_importance.to_csv(reports_dir / "shap_importance.csv", index=False)
    _save_shap_summary_plot(model, shap_frame, reports_dir / "shap_summary.png")

    joblib.dump(
        {
            "model_name": training.best_model_name,
            "model": model,
            "preprocessor": training.preprocessor,
            "feature_names": training.X_train.columns.tolist(),
            "threshold": 0.5,
        },
        models_dir / "rogue_model.pkl",
    )

    sample_idx = int(np.argmax(probabilities))
    inference_example = {
        "example_index": sample_idx,
        "predicted_probability": float(probabilities[sample_idx]),
        "predicted_label": int(predictions[sample_idx]),
        "true_label": int(y_test.iloc[sample_idx]),
        "top_features": _to_native(
            X_test.iloc[sample_idx]
            .reindex(feature_importance["feature"].head(8))
            .round(4)
            .to_dict()
        ),
    }

    metadata = {
        "project_name": "RogueGuard – Rogue Wave Risk Prediction",
        "best_model": training.best_model_name,
        "performance_metrics": metrics,
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
        "precision_recall_auc": pr_auc,
        "roc_auc_curve": roc_auc,
        "top_feature_importance": _to_native(feature_importance.head(20).to_dict(orient="records")),
        "top_shap_features": _to_native(shap_importance.head(20).to_dict(orient="records")),
        "inference_example": inference_example,
        "training_metadata": _to_native(training.metadata),
        "artifacts": {
            "confusion_matrix": str((reports_dir / "confusion_matrix.png").resolve()),
            "roc_curve": str((reports_dir / "roc_curve.png").resolve()),
            "precision_recall_curve": str((reports_dir / "precision_recall_curve.png").resolve()),
            "feature_importance_csv": str((reports_dir / "feature_importance.csv").resolve()),
            "shap_importance_csv": str((reports_dir / "shap_importance.csv").resolve()),
            "shap_summary": str((reports_dir / "shap_summary.png").resolve()),
            "model_pickle": str((models_dir / "rogue_model.pkl").resolve()),
        },
        "handoff_notes": [
            "This model predicts a proxy rogue-risk label, not confirmed rogue-wave events.",
            "Inference must apply the same engineered-feature and preprocessing logic used in training.",
            "The training split is chronological; future validation should preserve temporal ordering.",
            "If the team collects verified incident labels later, retraining against real events should take priority over tuning this proxy target.",
        ],
    }
    (models_dir / "metadata.json").write_text(json.dumps(_to_native(metadata), indent=2), encoding="utf-8")

    feature_importance_text = feature_importance.head(10).to_string(index=False)
    shap_importance_text = shap_importance.head(10).to_string(index=False)

    report = f"""# RogueGuard Final ML Report

## Best Model
- Model: {training.best_model_name}
- Accuracy: {metrics['accuracy']:.4f}
- Precision: {metrics['precision']:.4f}
- Recall: {metrics['recall']:.4f}
- F1: {metrics['f1']:.4f}
- ROC AUC: {metrics['roc_auc']:.4f}
- PR AUC: {pr_auc:.4f}

## Confusion Matrix
- TN: {tn}
- FP: {fp}
- FN: {fn}
- TP: {tp}

## Top Feature Rankings
### Model Importance
```
{feature_importance_text}
```

### SHAP Importance
```
{shap_importance_text}
```

## Inference Example
- Example index: {inference_example['example_index']}
- Predicted probability: {inference_example['predicted_probability']:.4f}
- Predicted label: {inference_example['predicted_label']}
- True label: {inference_example['true_label']}

## Handoff Notes
- This system predicts potential rogue-wave risk from a proxy severity label, not verified rogue-wave events.
- Production inference must preserve the feature engineering, categorical encoding, and robust scaling used in training.
- Any future frontend/backend integration should load `models/rogue_model.pkl` and the metadata in `models/metadata.json`.
- Future data collection should prioritize verified incident labels and site-specific measurements to reduce proxy-target bias.
"""
    (reports_dir / "final_ml_report.md").write_text(report, encoding="utf-8")

    return metadata


if __name__ == "__main__":
    data_root = Path(r"C:\Users\revan\Downloads\archive")
    metadata = evaluate_and_export(data_root)
    print(json.dumps(_to_native(metadata), indent=2))
