from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request

from backend.app.api.deps import get_db, settings_dep
from backend.app.core.config import APP_NAME, APP_VERSION
from backend.app.schemas.system import HealthResponse, ModelStatusResponse
from backend.app.services import analyses
from backend.app.services import system as system_service
from ml.config import EVALUATION_FILENAME

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    return HealthResponse(
        status="ok", app=APP_NAME, version=APP_VERSION, checked_at=datetime.now(timezone.utc),
        model_loaded=request.app.state.predictor is not None, live_capture="not_implemented")


@router.get("/model/status", response_model=ModelStatusResponse)
def model_status(request: Request) -> ModelStatusResponse:
    predictor = request.app.state.predictor
    if predictor is None:
        return ModelStatusResponse(
            loaded=False, message=request.app.state.model_error or "No trained model found. Train a model first.")
    return ModelStatusResponse(loaded=True, message="Model loaded successfully.", metadata=predictor.metadata)


@router.get("/system/info", tags=["system"])
def system_info(request: Request, settings=Depends(settings_dep)):
    return system_service.system_info(settings, request.app.state.predictor, request.app.state.model_error)


@router.get("/overview", tags=["analyses"])
def overview(request: Request, db=Depends(get_db), settings=Depends(settings_dep)):
    return analyses.overview(db, request.app.state.predictor,
                             (settings.artifacts_dir / EVALUATION_FILENAME).is_file())
