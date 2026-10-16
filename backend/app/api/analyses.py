from fastapi import APIRouter, Depends, Query

from backend.app.api.deps import get_db, require_predictor, settings_dep
from backend.app.core.errors import BadRequestError
from backend.app.schemas.requests import AnalysisCreate
from backend.app.services import analyses

router = APIRouter(prefix="/api", tags=["analyses"])


@router.post("/analyses", status_code=201)
def create_analysis(body: AnalysisCreate, db=Depends(get_db), settings=Depends(settings_dep),
                    predictor=Depends(require_predictor)):
    if body.source == "dataset":
        if body.dataset_id is None:
            raise BadRequestError("dataset_id is required when source is 'dataset'.")
        return analyses.analyse_dataset(db, settings.uploads_dir, predictor, body.dataset_id)
    return analyses.analyse_synthetic(db, predictor, body.synthetic_rows, body.seed)


@router.get("/analyses")
def list_analyses(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=200), db=Depends(get_db)):
    return analyses.list_analyses(db, page, page_size)


@router.get("/analyses/{analysis_id}")
def get_analysis(analysis_id: int, db=Depends(get_db)):
    return analyses.analysis_summary(db, analysis_id)


@router.get("/flows")
def list_flows(analysis_id: int | None = None, page: int = Query(1, ge=1),
               page_size: int = Query(25, ge=1, le=200), search: str | None = Query(None, max_length=100),
               classification: str | None = None, attack_class: str | None = None,
               protocol: str | None = None, min_confidence: float | None = Query(None, ge=0, le=1),
               max_confidence: float | None = Query(None, ge=0, le=1), sort_by: str = "row_index",
               sort_dir: str = "asc", db=Depends(get_db)):
    return analyses.list_flows(db, analysis_id, page, page_size, search, classification, attack_class,
                               protocol, min_confidence, max_confidence, sort_by, sort_dir)


@router.get("/flows/facets")
def flow_facets(analysis_id: int | None = None, db=Depends(get_db)):
    return analyses.facets(db, analysis_id)


@router.get("/flows/{flow_id}")
def get_flow(flow_id: int, db=Depends(get_db)):
    return analyses.get_flow(db, flow_id)
