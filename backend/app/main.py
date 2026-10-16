from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api import alerts, analyses, datasets, exports, models, predictions, system
from backend.app.core.config import APP_NAME, APP_VERSION, CORS_ORIGINS, get_settings
from backend.app.core.errors import (BadRequestError, ConflictError, NotFoundError,
                                     PayloadTooLargeError)
from backend.app.database.db import init_db
from ml.predict import ModelNotTrainedError, Predictor, PredictionInputError
from ml.preprocessing import DatasetError


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    init_db(settings.db_path)
    app.state.predictor = None
    app.state.model_error = None
    try:
        app.state.predictor = Predictor.load(settings.artifacts_dir)
    except ModelNotTrainedError as exc:
        app.state.model_error = str(exc)
    yield


app = FastAPI(title=f"{APP_NAME} API", version=APP_VERSION,
              description="ML-based intrusion detection prototype for simulated 5G/IoT traffic. "
                          "Analyses recorded flow datasets; live capture is not implemented.",
              lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS,
                   allow_methods=["GET", "POST", "PATCH"], allow_headers=["*"])

for module in (system, datasets, models, predictions, analyses, alerts, exports):
    app.include_router(module.router)

_ERROR_STATUS = ((NotFoundError, 404), (ConflictError, 409), (ModelNotTrainedError, 409),
                 (PayloadTooLargeError, 413), (BadRequestError, 400), (DatasetError, 422),
                 (PredictionInputError, 422))


def _register(exc_type, status):
    @app.exception_handler(exc_type)
    async def handler(request: Request, exc):
        return JSONResponse(status_code=status, content={"detail": str(exc)})


for _exc, _status in _ERROR_STATUS:
    _register(_exc, _status)
