from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

CURRENT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = CURRENT_DIR.parent
PKG_DIR = WORKSPACE_ROOT / ".python_pkgs"
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from xgboost import XGBClassifier

from labeling import LABEL_COLUMN
from preprocess import prepare_preprocessed_data


RANDOM_STATE = 42


@dataclass
class TrainingArtifacts:
    results: pd.DataFrame
    best_model_name: str
    best_model: Any
    X_train: pd.DataFrame
    X_test: pd.DataFrame
    y_train: pd.Series
    y_test: pd.Series
    preprocessor: Any
    metadata: dict[str, Any]


def _build_models(scale_pos_weight: float) -> dict[str, Any]:
    return {
        "Random Forest": RandomForestClassifier(
            n_estimators=300,
            max_depth=10,
            min_samples_leaf=4,
            class_weight="balanced_subsample",
            n_jobs=-1,
            random_state=RANDOM_STATE,
        ),
        "XGBoost": XGBClassifier(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.85,
            colsample_bytree=0.85,
            reg_lambda=1.0,
            min_child_weight=3,
            objective="binary:logistic",
            eval_metric="logloss",
            scale_pos_weight=scale_pos_weight,
            random_state=RANDOM_STATE,
            n_jobs=4,
        ),
        "LightGBM": LGBMClassifier(
            n_estimators=300,
            learning_rate=0.05,
            num_leaves=31,
            subsample=0.85,
            colsample_bytree=0.85,
            class_weight="balanced",
            random_state=RANDOM_STATE,
            verbose=-1,
        ),
    }


def train_and_compare_models(data_dir: str | Path) -> TrainingArtifacts:
    prepared = prepare_preprocessed_data(data_dir)
    X_train = prepared.X_train
    X_test = prepared.X_test
    y_train = prepared.y_train
    y_test = prepared.y_test

    positive_count = int(y_train.sum())
    negative_count = int(len(y_train) - positive_count)
    scale_pos_weight = negative_count / max(positive_count, 1)

    rows = []
    fitted_models: dict[str, Any] = {}
    for model_name, model in _build_models(scale_pos_weight).items():
        model.fit(X_train, y_train)
        probabilities = model.predict_proba(X_test)[:, 1]
        predictions = (probabilities >= 0.5).astype(int)

        metrics = {
            "model": model_name,
            "accuracy": float(accuracy_score(y_test, predictions)),
            "precision": float(precision_score(y_test, predictions, zero_division=0)),
            "recall": float(recall_score(y_test, predictions, zero_division=0)),
            "f1": float(f1_score(y_test, predictions, zero_division=0)),
            "roc_auc": float(roc_auc_score(y_test, probabilities)),
            "positive_predictions": int(predictions.sum()),
        }
        rows.append(metrics)
        fitted_models[model_name] = model

    results = pd.DataFrame(rows).sort_values(
        by=["roc_auc", "f1", "recall", "precision", "accuracy"],
        ascending=False,
    ).reset_index(drop=True)
    best_model_name = str(results.iloc[0]["model"])
    best_model = fitted_models[best_model_name]

    metadata = {
        "split_metadata": prepared.metadata,
        "target_column": LABEL_COLUMN,
        "scale_pos_weight": float(scale_pos_weight),
        "feature_count": int(X_train.shape[1]),
        "train_positive_count": positive_count,
        "train_negative_count": negative_count,
    }

    return TrainingArtifacts(
        results=results,
        best_model_name=best_model_name,
        best_model=best_model,
        X_train=X_train,
        X_test=X_test,
        y_train=y_train,
        y_test=y_test,
        preprocessor=prepared.preprocessor,
        metadata=metadata,
    )


if __name__ == "__main__":
    data_root = Path(r"C:\Users\revan\Downloads\archive")
    artifacts = train_and_compare_models(data_root)
    print("Best model:", artifacts.best_model_name)
    print(artifacts.results.to_string(index=False))
    print(json.dumps(artifacts.metadata, indent=2))
