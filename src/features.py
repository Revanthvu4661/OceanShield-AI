from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


RAW_RENAME_MAP = {
    "preciptation": "precipitation",
    "cloundover": "cloudcover",
    "name": "beach_name",
}


DEFAULT_DROP_COLUMNS = [
    "idhourforecast",
    "iddayforecast",
    "date",
    "sunrise",
    "sunset",
    "moonrise",
    "moonset",
    "city",
    "state",
    "country",
    "beach_name",
    "latitude",
    "longitude",
    "temperature",
    "windchill",
    "heatIndex",
    "feelslike",
]


FEATURE_COLUMNS = [
    "hour_sin",
    "hour_cos",
    "daylight_flag",
    "daily_temp_range",
    "temperature_vs_daily_max",
    "temperature_vs_daily_min",
    "dewpoint_depression",
    "precipitation_log",
    "cloud_humidity_interaction",
    "wind_vector_x",
    "wind_vector_y",
    "swell_vector_x",
    "swell_vector_y",
    "directional_misalignment",
    "wind_alignment",
    "gust_factor",
    "gust_delta",
    "wind_intensity",
    "wave_energy",
    "wave_steepness",
    "wave_power_index",
    "swell_ratio",
    "swell_energy",
    "wave_severity",
    "wave_wind_interaction",
    "marine_risk_index",
    "pressure_anomaly",
    "pressure_drop_flag",
    "lunar_energy_proxy",
    "tide_height_normalized",
    "tide_extreme_imbalance",
]


@dataclass
class FeatureArtifacts:
    frame: pd.DataFrame
    feature_columns: list[str]
    dropped_columns: list[str]
    metadata: dict[str, Any]


def _read_csv(data_dir: Path, file_name: str) -> pd.DataFrame:
    return pd.read_csv(data_dir / file_name, sep=";")


def _aggregate_tide_features(tide: pd.DataFrame) -> pd.DataFrame:
    grouped = tide.groupby("iddayforecast")
    return (
        grouped.agg(
            tide_events=("idtide", "count"),
            tide_height_mean=("height", "mean"),
            tide_height_max=("height", "max"),
            tide_height_min=("height", "min"),
            tide_height_range=("height", lambda s: s.max() - s.min()),
            high_tide_count=("type", lambda s: (s == "HIGH").sum()),
            low_tide_count=("type", lambda s: (s == "LOW").sum()),
        )
        .reset_index()
    )


def load_modeling_frame(data_dir: str | Path) -> pd.DataFrame:
    data_path = Path(data_dir)
    beach = _read_csv(data_path, "beach.csv")
    day = _read_csv(data_path, "day_forecast.csv")
    hour = _read_csv(data_path, "hour_forecast.csv")
    tide = _read_csv(data_path, "tide.csv")

    tide_features = _aggregate_tide_features(tide)

    frame = (
        hour.merge(day, on="iddayforecast", how="left", suffixes=("", "_day"))
        .merge(beach, on="idbeach", how="left", suffixes=("", "_beach"))
        .merge(tide_features, on="iddayforecast", how="left")
        .rename(columns=RAW_RENAME_MAP)
    )

    frame["date"] = pd.to_datetime(frame["date"])
    frame["hour"] = (frame["time"] // 100).astype(int)
    frame["watertemp"] = frame["watertemp"].mask(frame["watertemp"] < 0, np.nan)
    return frame


def _minimal_angle_difference(a: pd.Series, b: pd.Series) -> pd.Series:
    return np.abs(((a - b + 180) % 360) - 180)


def engineer_features(frame: pd.DataFrame, drop_columns: list[str] | None = None) -> FeatureArtifacts:
    df = frame.copy()

    drop_columns = list(DEFAULT_DROP_COLUMNS if drop_columns is None else drop_columns)

    radians_wind = np.deg2rad(df["winddirdegree"])
    radians_swell = np.deg2rad(df["swelldir"])
    direction_gap = _minimal_angle_difference(df["winddirdegree"], df["swelldir"])

    daily_pressure_mean = df.groupby("iddayforecast")["pressure"].transform("mean")
    tide_midpoint = (df["tide_height_max"] + df["tide_height_min"]) / 2.0
    sigheight_safe = df["sigheight"].replace(0, np.nan)
    windspeed_safe = df["windspeed"].replace(0, np.nan)
    period_safe = df["period"].replace(0, np.nan)

    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24.0)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24.0)
    df["daylight_flag"] = ((df["hour"] >= 6) & (df["hour"] <= 18)).astype(int)

    df["daily_temp_range"] = df["maxtemp"] - df["mintemp"]
    df["temperature_vs_daily_max"] = df["maxtemp"] - df["temperature"]
    df["temperature_vs_daily_min"] = df["temperature"] - df["mintemp"]
    df["dewpoint_depression"] = df["temperature"] - df["dewpoint"]
    df["precipitation_log"] = np.log1p(df["precipitation"])
    df["cloud_humidity_interaction"] = (df["cloudcover"] / 100.0) * (df["humidity"] / 100.0)

    df["wind_vector_x"] = np.cos(radians_wind) * df["windspeed"]
    df["wind_vector_y"] = np.sin(radians_wind) * df["windspeed"]
    df["swell_vector_x"] = np.cos(radians_swell) * df["swellheight"]
    df["swell_vector_y"] = np.sin(radians_swell) * df["swellheight"]
    df["directional_misalignment"] = direction_gap / 180.0
    df["wind_alignment"] = np.cos(np.deg2rad(direction_gap))

    df["gust_factor"] = (df["windgust"] / windspeed_safe).fillna(0.0)
    df["gust_delta"] = df["windgust"] - df["windspeed"]
    df["wind_intensity"] = 0.7 * df["windspeed"] + 0.3 * df["windgust"]

    df["wave_energy"] = (df["sigheight"] ** 2) * df["period"]
    df["wave_steepness"] = (df["sigheight"] / period_safe).fillna(0.0)
    df["wave_power_index"] = df["sigheight"] * df["swellheight"] * df["period"]
    df["swell_ratio"] = (df["swellheight"] / sigheight_safe).fillna(0.0)
    df["swell_energy"] = (df["swellheight"] ** 2) * df["period"]
    df["wave_severity"] = (
        0.40 * df["sigheight"]
        + 0.25 * df["swellheight"]
        + 0.20 * (df["period"] / df["period"].median())
        + 0.15 * (df["windgust"] / df["windgust"].median())
    )
    df["wave_wind_interaction"] = df["sigheight"] * df["wind_intensity"]

    df["pressure_anomaly"] = df["pressure"] - daily_pressure_mean
    df["pressure_drop_flag"] = (df["pressure_anomaly"] <= -2).astype(int)
    df["lunar_energy_proxy"] = df["moon_illumination"] / 100.0

    df["tide_height_normalized"] = (
        (df["tide_height_mean"] - tide_midpoint) / df["tide_height_range"].replace(0, np.nan)
    ).fillna(0.0)
    df["tide_extreme_imbalance"] = df["high_tide_count"] - df["low_tide_count"]

    df["marine_risk_index"] = (
        0.28 * df["wave_energy"]
        + 0.20 * df["wave_power_index"]
        + 0.15 * df["wind_intensity"]
        + 0.12 * df["gust_factor"]
        + 0.10 * df["directional_misalignment"]
        + 0.10 * df["tide_height_range"]
        - 0.05 * df["pressure_anomaly"]
    )

    drop_candidates = [column for column in drop_columns if column in df.columns]
    final_df = df.drop(columns=drop_candidates)

    metadata = {
        "row_count": int(final_df.shape[0]),
        "column_count": int(final_df.shape[1]),
        "engineered_feature_count": len(FEATURE_COLUMNS),
        "dropped_columns": drop_candidates,
        "null_counts_after_engineering": final_df.isna().sum().loc[lambda s: s > 0].to_dict(),
    }

    return FeatureArtifacts(
        frame=final_df,
        feature_columns=list(FEATURE_COLUMNS),
        dropped_columns=drop_candidates,
        metadata=metadata,
    )


def build_feature_frame(data_dir: str | Path, drop_columns: list[str] | None = None) -> FeatureArtifacts:
    raw_frame = load_modeling_frame(data_dir)
    return engineer_features(raw_frame, drop_columns=drop_columns)


if __name__ == "__main__":
    data_root = Path(r"C:\Users\revan\Downloads\archive")
    artifacts = build_feature_frame(data_root)
    print("Engineered rows:", artifacts.metadata["row_count"])
    print("Engineered columns:", artifacts.metadata["column_count"])
    print("Feature columns:", ", ".join(artifacts.feature_columns))
    print("Dropped columns:", ", ".join(artifacts.dropped_columns))
    print("Remaining null counts:", artifacts.metadata["null_counts_after_engineering"])
