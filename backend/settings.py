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
BACKEND_RUNTIME_DIR = ROOT_DIR / "runtime"
BACKGROUND_DB_PATH = BACKEND_RUNTIME_DIR / "background_state.sqlite3"

DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
BACKGROUND_POLL_INTERVAL_SECONDS = int(os.getenv("BACKGROUND_POLL_INTERVAL_SECONDS", "10800"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
DAILY_BRIEFING_UTC_HOUR = int(os.getenv("DAILY_BRIEFING_UTC_HOUR", "6"))
DAILY_BRIEFING_LOOKBACK_HOURS = int(os.getenv("DAILY_BRIEFING_LOOKBACK_HOURS", "24"))
