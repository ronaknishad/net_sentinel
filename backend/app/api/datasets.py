from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from backend.app.api.deps import get_db, settings_dep
from backend.app.schemas.requests import RevalidateRequest
from backend.app.services import datasets as svc

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.get("")
def list_datasets(db=Depends(get_db)):
    return {"items": svc.list_datasets(db)}


@router.post("/upload", status_code=201)
def upload_dataset(file: UploadFile = File(...), label_column: str | None = Form(None),
                   is_synthetic: bool = Form(False), db=Depends(get_db), settings=Depends(settings_dep)):
    """Validate and store a CSV. The file is parsed as data only; its contents are never executed."""
    return svc.save_upload(db, settings.uploads_dir, file.filename, file.file, label_column, is_synthetic)


@router.post("/sample", status_code=201)
def register_sample(db=Depends(get_db), settings=Depends(settings_dep)):
    """Register the bundled SYNTHETIC demonstration dataset."""
    return svc.register_bundled_sample(db, settings.uploads_dir)


@router.get("/{dataset_id}")
def get_dataset(dataset_id: int, db=Depends(get_db)):
    return svc.get_dataset(db, dataset_id)


@router.get("/{dataset_id}/preview")
def preview_dataset(dataset_id: int, rows: int = Query(10, ge=1, le=50), db=Depends(get_db),
                    settings=Depends(settings_dep)):
    return svc.preview(db, settings.uploads_dir, dataset_id, rows)


@router.post("/{dataset_id}/validate")
def revalidate_dataset(dataset_id: int, body: RevalidateRequest, db=Depends(get_db),
                       settings=Depends(settings_dep)):
    """Re-run validation with a chosen label column and/or explicit feature mapping."""
    return svc.revalidate(db, settings.uploads_dir, dataset_id, body.label_column,
                          body.column_overrides, body.is_synthetic)
