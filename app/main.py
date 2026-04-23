import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import configure_logging


configure_logging()

_settings = get_settings()
if _settings.paddle_pdx_disable_model_source_check:
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

app = FastAPI(title="Medication Label Reader MVP", version="1.0.0")

app.include_router(router)

_static_dir = Path(__file__).resolve().parents[1] / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")
