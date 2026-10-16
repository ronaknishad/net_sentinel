from fastapi import APIRouter, Depends, Request

from backend.app.api.deps import get_db, settings_dep
from backend.app.schemas.requests import TrainRequest
from backend.app.services import exports, training
from ml.predict import ModelNotTrainedError, Predictor

router = APIRouter(prefix="/api/models", tags=["models"])


def _reload(app):
    def reload_model():
        try:
            app.state.predictor = Predictor.load(settings_dep().artifacts_dir)
            app.state.model_error = None
        except ModelNotTrainedError as exc:
            app.state.predictor, app.state.model_error = None, str(exc)
    return reload_model


@router.post("/train", status_code=202)
def start_training(body: TrainRequest, request: Request, settings=Depends(settings_dep)):
    """Start a background training job. Poll GET /api/models/train/{run_id}."""
    return training.start_training(settings.db_path, settings.uploads_dir, settings.artifacts_dir,
                                   body.dataset_id, body.mode, body.confirm, _reload(request.app))


@router.get("/train")
def list_training_runs(db=Depends(get_db)):
    return {"items": training.list_runs(db)}


@router.get("/train/{run_id}")
def get_training_run(run_id: int, db=Depends(get_db)):
    return training.get_run(db, run_id)


@router.get("/evaluation")
def get_evaluation(settings=Depends(settings_dep)):
    return exports.load_evaluation(settings.artifacts_dir)
