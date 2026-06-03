from __future__ import annotations

import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
MODEL_DIR = ROOT_DIR / "models"
SRC_DIR = ROOT_DIR / "src"
MODEL_BUNDLE_PATH = MODEL_DIR / "rogue_model.pkl"
METADATA_PATH = MODEL_DIR / "metadata.json"
LOCAL_DEPENDENCY_DIR = ROOT_DIR / ".python_pkgs"

DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
