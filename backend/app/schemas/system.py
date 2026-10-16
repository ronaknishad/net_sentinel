from datetime import datetime

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    checked_at: datetime
    model_loaded: bool
    live_capture: str


class ModelMetadata(BaseModel):
    model_id: str
    model_name: str
    mode: str
    dataset_name: str
    is_synthetic: bool
    trained_at: str
    schema_version: str
    classes: list[str]
    feature_names: list[str]


class ModelStatusResponse(BaseModel):
    loaded: bool
    message: str
    metadata: ModelMetadata | None = None
