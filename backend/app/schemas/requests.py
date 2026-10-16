from typing import Any, Literal

from pydantic import BaseModel, Field


class RevalidateRequest(BaseModel):
    label_column: str | None = None
    column_overrides: dict[str, str] | None = Field(
        default=None, description="Explicit mapping {supported_feature: csv_column}")
    is_synthetic: bool | None = None


class TrainRequest(BaseModel):
    dataset_id: int
    mode: Literal["binary", "multiclass"] = "multiclass"
    confirm: bool = Field(default=False, description="Must be true: training can be slow on large files.")


class PredictionRequest(BaseModel):
    record: dict[str, Any] = Field(description="One flow using supported feature names or CIC headers")
    save: bool = Field(default=False, description="Store the result as an analysis (creates an alert if suspicious)")


class AnalysisCreate(BaseModel):
    source: Literal["dataset", "synthetic"]
    dataset_id: int | None = None
    synthetic_rows: int = Field(default=500, ge=10, le=5000)
    seed: int = 7


class AlertUpdate(BaseModel):
    status: Literal["new", "under_review", "resolved"]
