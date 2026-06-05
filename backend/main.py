from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
if str(ROOT_DIR / ".python_pkgs") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / ".python_pkgs"))

from predictor import get_metadata, get_model
from alerts import alert_dispatcher_loop
from background_jobs import background_loop, daily_briefing_loop
from routes.ai_search import router as ai_search_router
from routes.alerts import router as alerts_router
from routes.briefings import router as briefings_router
from routes.background import router as background_router
from routes.explain import router as explain_router
from routes.health import router as health_router
from routes.model_meta import router as model_meta_router
from routes.predict import router as predict_router
from settings import FRONTEND_DIR
from storage import initialize_background_store


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("oceanshield")

app = FastAPI(title="OceanShield AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
app.include_router(health_router, prefix="/api")
app.include_router(predict_router, prefix="/api")
app.include_router(explain_router, prefix="/api")
app.include_router(ai_search_router, prefix="/api")
app.include_router(model_meta_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")
app.include_router(briefings_router, prefix="/api")
app.include_router(background_router, prefix="/api")

BACKGROUND_STOP_EVENT: asyncio.Event | None = None
BACKGROUND_TASKS: list[asyncio.Task] = []


@app.on_event("startup")
async def startup_event() -> None:
    global BACKGROUND_STOP_EVENT, BACKGROUND_TASKS
    model = get_model()
    metadata = get_metadata()
    metrics = metadata["performance_metrics"]
    initialize_background_store()
    logger.info(
        "Loaded %s with accuracy=%.4f f1=%.4f roc_auc=%.4f",
        metadata["best_model"],
        metrics["accuracy"],
        metrics["f1"],
        metrics["roc_auc"],
    )
    logger.info("Model class: %s", type(model).__name__)
    BACKGROUND_STOP_EVENT = asyncio.Event()
    BACKGROUND_TASKS = [
        asyncio.create_task(background_loop(BACKGROUND_STOP_EVENT)),
        asyncio.create_task(daily_briefing_loop(BACKGROUND_STOP_EVENT)),
        asyncio.create_task(alert_dispatcher_loop(BACKGROUND_STOP_EVENT)),
    ]


@app.on_event("shutdown")
async def shutdown_event() -> None:
    global BACKGROUND_STOP_EVENT, BACKGROUND_TASKS
    if BACKGROUND_STOP_EVENT is not None:
        BACKGROUND_STOP_EVENT.set()
    for task in BACKGROUND_TASKS:
        task.cancel()
    for task in BACKGROUND_TASKS:
        try:
            await task
        except asyncio.CancelledError:
            pass


@app.get("/")
def serve_index() -> FileResponse:
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}
