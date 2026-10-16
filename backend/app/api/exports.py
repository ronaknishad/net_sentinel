import json

from fastapi import APIRouter, Depends, Response

from backend.app.api.deps import get_db, settings_dep
from backend.app.core.errors import BadRequestError
from backend.app.services import exports

router = APIRouter(prefix="/api/exports", tags=["exports"])


@router.get("/evaluation")
def export_evaluation(format: str = "json", settings=Depends(settings_dep)):
    if format not in ("json", "csv"):
        raise BadRequestError("format must be 'json' or 'csv'.")
    evaluation = exports.load_evaluation(settings.artifacts_dir)
    if format == "csv":
        body, media = exports.evaluation_csv(evaluation), "text/csv"
    else:
        body, media = json.dumps(evaluation, indent=2), "application/json"
    return Response(body, media_type=media, headers={
        "Content-Disposition": f'attachment; filename="netsentinel_evaluation.{format}"'})


@router.get("/analyses/{analysis_id}")
def export_analysis(analysis_id: int, db=Depends(get_db)):
    return Response(exports.flows_csv(db, analysis_id), media_type="text/csv", headers={
        "Content-Disposition": f'attachment; filename="netsentinel_analysis_{analysis_id}.csv"'})
