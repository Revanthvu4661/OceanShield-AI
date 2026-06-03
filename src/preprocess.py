from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from features import DEFAULT_DROP_COLUMNS, engineer_features, load_modeling_frame
from labeling import LABEL_COLUMN, create_proxy_label


CATEGORICAL_COLUMNS = ["moon_phase", "idbeach"]
LEAKAGE_COLUMNS = [
    LABEL_COLUMN,
    "rogue_risk_score",
    "sigheight_flag",
    "swellheight_flag",
    "period_flag",
    "windspeed_flag",
    "threshold_hit_count",
]
NON_MODEL_COLUMNS = ["date", "time", "hour"]


@dataclass
class PreprocessorState:
    numeric_columns: list[str]
    categorical_columns: list[str]
    medians: dict[str, float]
    scales: dict[str, float]
    category_levels: dict[str, list[str]]


@dataclass
class PreprocessingArtifacts:
    X_train: pd.DataFrame
    X_test: pd.DataFrame
    y_train: pd.Series
    y_test: pd.Series
    train_frame: pd.DataFrame
    test_frame: pd.DataFrame
    feature_names: list[str]
    preprocessor: "RoguePreprocessor"
    metadata: dict[str, Any]


class RoguePreprocessor:
    def __init__(
        self,
        categorical_columns: list[str] | None = None,
        leakage_columns: list[str] | None = None,
        non_model_columns: list[str] | None = None,
    ) -> None:
        self.categorical_columns = list(CATEGORICAL_COLUMNS if categorical_columns is None else categorical_columns)
        self.leakage_columns = list(LEAKAGE_COLUMNS if leakage_columns is None else leakage_columns)
        self.non_model_columns = list(NON_MODEL_COLUMNS if non_model_columns is None else non_model_columns)
        self.state: PreprocessorState | None = None

    def _candidate_feature_columns(self, frame: pd.DataFrame) -> list[str]:
        blocked = set(self.leakage_columns + self.non_model_columns)
        return [column for column in frame.columns if column not in blocked]

    def fit(self, frame: pd.DataFrame, target_column: str = LABEL_COLUMN) -> "RoguePreprocessor":
        feature_columns = self._candidate_feature_columns(frame)

        categorical_columns = [column for column in self.categorical_columns if column in feature_columns]
        numeric_columns = [column for column in feature_columns if column not in categorical_columns]

        work = frame[feature_columns].copy()

        for column in categorical_columns:
            work[column] = work[column].astype("string").fillna("__missing__")

        medians = {}
        scales = {}
        for column in numeric_columns:
            series = pd.to_numeric(work[column], errors="coerce")
            median = float(series.median())
            q1 = float(series.quantile(0.25))
            q3 = float(series.quantile(0.75))
            iqr = q3 - q1
            medians[column] = median
            scales[column] = float(iqr if iqr not in (0.0, np.nan) and not np.isnan(iqr) else 1.0)
            if scales[column] == 0.0:
                scales[column] = 1.0

        category_levels = {}
        for column in categorical_columns:
            observed = sorted(work[column].astype("string").fillna("__missing__").unique().tolist())
            if "__unknown__" not in observed:
                observed.append("__unknown__")
            category_levels[column] = observed

        self.state = PreprocessorState(
            numeric_columns=numeric_columns,
            categorical_columns=categorical_columns,
            medians=medians,
            scales=scales,
            category_levels=category_levels,
        )
        return self

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        if self.state is None:
            raise ValueError("Preprocessor must be fitted before calling transform().")

        pieces: list[pd.DataFrame] = []

        numeric = frame[self.state.numeric_columns].copy()
        for column in self.state.numeric_columns:
            series = pd.to_numeric(numeric[column], errors="coerce").fillna(self.state.medians[column])
            numeric[column] = (series - self.state.medians[column]) / self.state.scales[column]
        pieces.append(numeric)

        for column in self.state.categorical_columns:
            values = frame[column].astype("string").fillna("__missing__")
            known_levels = set(self.state.category_levels[column])
            values = values.where(values.isin(known_levels), "__unknown__")
            encoded = pd.get_dummies(values, prefix=column, dtype=float)
            expected_columns = [f"{column}_{level}" for level in self.state.category_levels[column]]
            encoded = encoded.reindex(columns=expected_columns, fill_value=0.0)
            pieces.append(encoded)

        transformed = pd.concat(pieces, axis=1)
        return transformed.reindex(sorted(transformed.columns), axis=1)

    def fit_transform(self, frame: pd.DataFrame, target_column: str = LABEL_COLUMN) -> pd.DataFrame:
        return self.fit(frame, target_column=target_column).transform(frame)


def build_labeled_modeling_frame(data_dir: str | Path) -> pd.DataFrame:
    raw = load_modeling_frame(data_dir)
    drop_columns = [column for column in DEFAULT_DROP_COLUMNS if column != "date"]
    featured = engineer_features(raw, drop_columns=drop_columns)
    labeled = create_proxy_label(featured.frame)
    return labeled.frame


def chronological_train_test_split(
    frame: pd.DataFrame,
    date_column: str = "date",
    test_fraction: float = 0.2,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    if date_column not in frame.columns:
        raise ValueError(f"Expected '{date_column}' to exist for chronological splitting.")

    unique_dates = np.array(sorted(frame[date_column].dt.normalize().unique()))
    cutoff_index = max(1, int(len(unique_dates) * (1 - test_fraction)))
    train_dates = unique_dates[:cutoff_index]
    test_dates = unique_dates[cutoff_index:]
    if len(test_dates) == 0:
        raise ValueError("Test split is empty. Adjust test_fraction.")

    train_frame = frame[frame[date_column].dt.normalize().isin(train_dates)].copy()
    test_frame = frame[frame[date_column].dt.normalize().isin(test_dates)].copy()

    metadata = {
        "split_strategy": "chronological",
        "train_end_date": str(pd.Timestamp(train_dates[-1]).date()),
        "test_start_date": str(pd.Timestamp(test_dates[0]).date()),
        "train_unique_dates": int(len(train_dates)),
        "test_unique_dates": int(len(test_dates)),
    }
    return train_frame, test_frame, metadata


def prepare_preprocessed_data(
    data_dir: str | Path,
    target_column: str = LABEL_COLUMN,
    test_fraction: float = 0.2,
) -> PreprocessingArtifacts:
    frame = build_labeled_modeling_frame(data_dir)
    train_frame, test_frame, split_metadata = chronological_train_test_split(
        frame, date_column="date", test_fraction=test_fraction
    )

    preprocessor = RoguePreprocessor()
    X_train = preprocessor.fit_transform(train_frame, target_column=target_column)
    X_test = preprocessor.transform(test_frame)
    y_train = train_frame[target_column].astype(int).reset_index(drop=True)
    y_test = test_frame[target_column].astype(int).reset_index(drop=True)
    X_train = X_train.reset_index(drop=True)
    X_test = X_test.reset_index(drop=True)

    metadata = {
        **split_metadata,
        "target_column": target_column,
        "train_rows": int(len(train_frame)),
        "test_rows": int(len(test_frame)),
        "train_positive_rate": float(y_train.mean()),
        "test_positive_rate": float(y_test.mean()),
        "feature_count": int(X_train.shape[1]),
        "categorical_columns": preprocessor.state.categorical_columns if preprocessor.state else [],
        "numeric_columns": preprocessor.state.numeric_columns if preprocessor.state else [],
        "excluded_columns": sorted(set(preprocessor.leakage_columns + preprocessor.non_model_columns)),
        "remaining_nulls_after_transform_train": int(X_train.isna().sum().sum()),
        "remaining_nulls_after_transform_test": int(X_test.isna().sum().sum()),
    }

    return PreprocessingArtifacts(
        X_train=X_train,
        X_test=X_test,
        y_train=y_train,
        y_test=y_test,
        train_frame=train_frame,
        test_frame=test_frame,
        feature_names=X_train.columns.tolist(),
        preprocessor=preprocessor,
        metadata=metadata,
    )


if __name__ == "__main__":
    data_root = Path(r"C:\Users\revan\Downloads\archive")
    artifacts = prepare_preprocessed_data(data_root)
    print("Split strategy:", artifacts.metadata["split_strategy"])
    print("Train end date:", artifacts.metadata["train_end_date"])
    print("Test start date:", artifacts.metadata["test_start_date"])
    print("Train rows:", artifacts.metadata["train_rows"])
    print("Test rows:", artifacts.metadata["test_rows"])
    print("Train positive rate:", round(artifacts.metadata["train_positive_rate"] * 100, 2))
    print("Test positive rate:", round(artifacts.metadata["test_positive_rate"] * 100, 2))
    print("Feature count:", artifacts.metadata["feature_count"])
    print("Remaining nulls (train/test):", artifacts.metadata["remaining_nulls_after_transform_train"], artifacts.metadata["remaining_nulls_after_transform_test"])
