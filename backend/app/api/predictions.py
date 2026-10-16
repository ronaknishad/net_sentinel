from fastapi import APIRouter, Depends

from backend.app.api.deps import get_db, require_predictor
from backend.app.schemas.requests import PredictionRequest
from backend.app.services import analyses
from ml.predict import PROBABILITY_NOTE

router = APIRouter(prefix="/api/predictions", tags=["predictions"])


@router.get("/samples")
def sample_records():
    """Synthetic example flows (one per class) for trying Mode B."""
    return {"items": analyses.sample_records()}


@router.post("")
def predict_record(body: PredictionRequest, db=Depends(get_db), predictor=Depends(require_predictor)):
    """Classify one flow record. Missing or non-numeric fields are rejected."""
    prediction = predictor.predict_record(body.record)
    meta = predictor.metadata
    out = {"prediction": prediction, "probability_note": PROBABILITY_NOTE,
           "model": {k: meta[k] for k in ("model_id", "model_name", "mode", "is_synthetic")},
           "message": f"Prediction completed using {meta['model_name']}.", "analysis_id": None}
    if body.save:
        out["analysis_id"] = analyses.analyse_record(db, predictor, body.record)["id"]
    return out
