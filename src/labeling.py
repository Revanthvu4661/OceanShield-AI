from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from features import build_feature_frame


LABEL_COLUMN = "rogue_risk_label"
LABEL_SCORE_COLUMN = "rogue_risk_score"


@dataclass
class LabelArtifacts:
    frame: pd.DataFrame
    metadata: dict[str, Any]


DEFAULT_THRESHOLDS = {
    "sigheight": 1.1,
    "swellheight": 1.0,
    "period": 12.0,
    "windspeed": 27.0,
}


def create_proxy_label(
    frame: pd.DataFrame,
    thresholds: dict[str, float] | None = None,
    label_column: str = LABEL_COLUMN,
    score_column: str = LABEL_SCORE_COLUMN,
) -> LabelArtifacts:
    df = frame.copy()
    thresholds = dict(DEFAULT_THRESHOLDS if thresholds is None else thresholds)

    df["sigheight_flag"] = (df["sigheight"] >= thresholds["sigheight"]).astype(int)
    df["swellheight_flag"] = (df["swellheight"] >= thresholds["swellheight"]).astype(int)
    df["period_flag"] = (df["period"] >= thresholds["period"]).astype(int)
    df["windspeed_flag"] = (df["windspeed"] >= thresholds["windspeed"]).astype(int)

    df["threshold_hit_count"] = (
        df["sigheight_flag"] + df["swellheight_flag"] + df["period_flag"] + df["windspeed_flag"]
    )

    df[score_column] = (
        0.35 * (df["sigheight"] / thresholds["sigheight"])
        + 0.25 * (df["swellheight"] / thresholds["swellheight"])
        + 0.20 * (df["period"] / thresholds["period"])
        + 0.20 * (df["windspeed"] / thresholds["windspeed"])
    )

    wave_anchor = (df["sigheight_flag"] == 1) | (df["swellheight_flag"] == 1)
    multi_factor_extreme = df["threshold_hit_count"] >= 3
    reinforced_dual_condition = wave_anchor & (df["threshold_hit_count"] >= 2) & (df[score_column] >= 1.0)

    df[label_column] = (multi_factor_extreme | reinforced_dual_condition).astype(int)

    class_counts = df[label_column].value_counts().sort_index().to_dict()
    metadata = {
        "thresholds": thresholds,
        "class_counts": {int(k): int(v) for k, v in class_counts.items()},
        "positive_rate": float(df[label_column].mean()),
        "score_summary": df[score_column].describe().round(4).to_dict(),
        "threshold_hit_distribution": df["threshold_hit_count"].value_counts().sort_index().to_dict(),
    }
    return LabelArtifacts(frame=df, metadata=metadata)


def build_labeled_frame(data_dir: str | Path) -> LabelArtifacts:
    feature_artifacts = build_feature_frame(data_dir)
    return create_proxy_label(feature_artifacts.frame)


if __name__ == "__main__":
    data_root = Path(r"C:\Users\revan\Downloads\archive")
    artifacts = build_labeled_frame(data_root)
    print("Thresholds:", artifacts.metadata["thresholds"])
    print("Class counts:", artifacts.metadata["class_counts"])
    print("Positive rate:", round(artifacts.metadata["positive_rate"] * 100, 2))
    print("Threshold hit distribution:", artifacts.metadata["threshold_hit_distribution"])
