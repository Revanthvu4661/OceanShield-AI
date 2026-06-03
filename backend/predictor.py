from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib

from settings import LOCAL_DEPENDENCY_DIR, METADATA_PATH, MODEL_BUNDLE_PATH, SRC_DIR


if str(LOCAL_DEPENDENCY_DIR) not in sys.path:
    sys.path.insert(0, str(LOCAL_DEPENDENCY_DIR))

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


_MODEL_BUNDLE: dict[str, Any] | None = None
_METADATA: dict[str, Any] | None = None


def _load_metadata() -> dict[str, Any]:
    if not METADATA_PATH.exists():
        raise RuntimeError(f"Metadata file not found: {METADATA_PATH}")
    return json.loads(METADATA_PATH.read_text(encoding="utf-8"))


def _load_bundle() -> dict[str, Any]:
    if not MODEL_BUNDLE_PATH.exists():
        raise RuntimeError(f"Model bundle not found: {MODEL_BUNDLE_PATH}")
    bundle = joblib.load(MODEL_BUNDLE_PATH)
    if not isinstance(bundle, dict) or "model" not in bundle:
        raise RuntimeError("rogue_model.pkl is not a valid OceanShield model bundle")
    return bundle


@lru_cache(maxsize=1)
def get_model_bundle() -> dict[str, Any]:
    global _MODEL_BUNDLE
    if _MODEL_BUNDLE is None:
        _MODEL_BUNDLE = _load_bundle()
    return _MODEL_BUNDLE


@lru_cache(maxsize=1)
def get_model() -> Any:
    return get_model_bundle()["model"]


@lru_cache(maxsize=1)
def get_preprocessor() -> Any:
    return get_model_bundle()["preprocessor"]


@lru_cache(maxsize=1)
def get_feature_names() -> list[str]:
    return list(get_model_bundle().get("feature_names", []))


@lru_cache(maxsize=1)
def get_metadata() -> dict[str, Any]:
    global _METADATA
    if _METADATA is None:
        _METADATA = _load_metadata()
    return _METADATA
