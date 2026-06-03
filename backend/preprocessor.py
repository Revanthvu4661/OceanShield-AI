from __future__ import annotations

from typing import Any

import pandas as pd

from feature_engine import engineer_single
from predictor import get_preprocessor
from schemas import OceanInput


def build_inference_frame(payload: OceanInput) -> pd.DataFrame:
    record = engineer_single(payload)
    return pd.DataFrame([record])


def transform_for_model(payload: OceanInput) -> pd.DataFrame:
    preprocessor = get_preprocessor()
    frame = build_inference_frame(payload)
    return preprocessor.transform(frame)


def get_preprocessor_state() -> Any:
    return get_preprocessor().state

