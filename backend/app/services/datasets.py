"""Dataset import, validation, preview and column overrides."""
from __future__ import annotations

import json
import shutil
import sqlite3
import uuid
from pathlib import Path

import numpy as np
import pandas as pd

from backend.app.core.config import MAX_UPLOAD_BYTES
from backend.app.core.errors import BadRequestError, NotFoundError, PayloadTooLargeError
from backend.app.database.db import utcnow
from ml.config import DEFAULT_DATA_DIR
from ml.feature_schema import ALIAS_INDEX, FEATURE_NAMES, normalize_name
from ml.preprocessing import DatasetError, load_csv, validate_dataframe

BUNDLED_SAMPLE = DEFAULT_DATA_DIR / "sample_synthetic_flows.csv"


def apply_overrides(df: pd.DataFrame, overrides: dict[str, str]) -> pd.DataFrame:
    """Explicit mapping {canonical_feature: csv_column}. Overrides win over automatic matching."""
    if not overrides:
        return df
    rename: dict[str, str] = {}
    for canon, orig in overrides.items():
        if canon not in FEATURE_NAMES:
            raise BadRequestError(f"'{canon}' is not a supported feature name.")
        if orig not in df.columns:
            raise BadRequestError(f"Column '{orig}' does not exist in this dataset.")
        rename[orig] = canon
    if len(set(rename.values())) != len(rename):
        raise BadRequestError("Two overrides point to the same feature.")
    for canon in rename.values():
        for col in df.columns:
            if col not in rename and ALIAS_INDEX.get(normalize_name(col)) == canon:
                rename[col] = f"{col} (unused)"
    return df.rename(columns=rename)


def _record(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["columns"] = json.loads(d.pop("columns_json"))
    d["validation"] = json.loads(d.pop("validation_json"))
    d["column_overrides"] = json.loads(d.pop("column_overrides_json"))
    d["is_synthetic"] = bool(d["is_synthetic"])
    d["is_valid"] = bool(d["is_valid"])
    d.pop("stored_name", None)
    return d


def _insert(db, uploads_dir: Path, stored_name: str, original: str, size: int,
            label_column, is_synthetic: bool) -> dict:
    path = uploads_dir / stored_name
    try:
        df = load_csv(path)
    except DatasetError:
        path.unlink(missing_ok=True)
        raise
    report = validate_dataframe(df, label_column)
    cur = db.execute(
        "INSERT INTO datasets (name, original_filename, stored_name, size_bytes, row_count, columns_json,"
        " label_column, is_synthetic, is_valid, validation_json, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (original, original, stored_name, size, len(df), json.dumps(list(df.columns)),
         report.label_column, int(is_synthetic), int(report.is_valid),
         json.dumps(report.to_dict()), utcnow()))
    db.commit()
    return get_dataset(db, cur.lastrowid)


def save_upload(db, uploads_dir: Path, filename: str, stream, label_column: str | None = None,
                is_synthetic: bool = False, max_bytes: int = MAX_UPLOAD_BYTES) -> dict:
    """Store an uploaded CSV under a generated name. The client filename is never used as a path."""
    display = Path(filename or "upload.csv").name[:120]
    if not display.lower().endswith(".csv"):
        raise BadRequestError("Only .csv files are supported.")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid.uuid4().hex}.csv"
    path = uploads_dir / stored
    size = 0
    try:
        with open(path, "wb") as out:
            while chunk := stream.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise PayloadTooLargeError(f"File exceeds the {max_bytes // (1024 * 1024)} MB upload limit.")
                out.write(chunk)
    except PayloadTooLargeError:
        path.unlink(missing_ok=True)
        raise
    return _insert(db, uploads_dir, stored, display, size, label_column, is_synthetic)


def register_bundled_sample(db, uploads_dir: Path) -> dict:
    """Copy the bundled SYNTHETIC sample into the dataset store."""
    if not BUNDLED_SAMPLE.is_file():
        raise NotFoundError("The bundled synthetic sample file is missing.")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid.uuid4().hex}.csv"
    shutil.copyfile(BUNDLED_SAMPLE, uploads_dir / stored)
    return _insert(db, uploads_dir, stored, "sample_synthetic_flows.csv (synthetic)",
                   (uploads_dir / stored).stat().st_size, None, True)


def list_datasets(db) -> list[dict]:
    rows = db.execute("SELECT * FROM datasets ORDER BY id DESC").fetchall()
    return [_record(r) for r in rows]


def get_dataset(db, dataset_id: int) -> dict:
    row = db.execute("SELECT * FROM datasets WHERE id=?", (dataset_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"Dataset {dataset_id} was not found.")
    return _record(row)


def _path(db, uploads_dir: Path, dataset_id: int) -> Path:
    row = db.execute("SELECT stored_name FROM datasets WHERE id=?", (dataset_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"Dataset {dataset_id} was not found.")
    path = uploads_dir / row["stored_name"]      # stored_name is generated server-side
    if not path.is_file():
        raise NotFoundError("The stored dataset file is missing from disk.")
    return path


def load_dataset_frame(db, uploads_dir: Path, dataset_id: int) -> tuple[pd.DataFrame, dict]:
    """Load the CSV and apply the saved column overrides."""
    ds = get_dataset(db, dataset_id)
    df = load_csv(_path(db, uploads_dir, dataset_id))
    return apply_overrides(df, ds["column_overrides"]), ds


def revalidate(db, uploads_dir: Path, dataset_id: int, label_column: str | None,
               column_overrides: dict[str, str] | None, is_synthetic: bool | None = None) -> dict:
    ds = get_dataset(db, dataset_id)
    overrides = ds["column_overrides"] if column_overrides is None else column_overrides
    df = load_csv(_path(db, uploads_dir, dataset_id))
    df = apply_overrides(df, overrides)
    report = validate_dataframe(df, label_column or ds["label_column"])
    synthetic = ds["is_synthetic"] if is_synthetic is None else is_synthetic
    db.execute("UPDATE datasets SET label_column=?, column_overrides_json=?, is_valid=?, "
               "validation_json=?, is_synthetic=? WHERE id=?",
               (report.label_column, json.dumps(overrides), int(report.is_valid),
                json.dumps(report.to_dict()), int(synthetic), dataset_id))
    db.commit()
    return get_dataset(db, dataset_id)


def preview(db, uploads_dir: Path, dataset_id: int, rows: int = 10) -> dict:
    path = _path(db, uploads_dir, dataset_id)
    df = pd.read_csv(path, nrows=max(1, min(rows, 50)), skipinitialspace=True, encoding_errors="replace")
    df.columns = [str(c).strip() for c in df.columns]

    def clean(v):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return None
        if isinstance(v, (float, np.floating)) and np.isinf(v):
            return "Infinity" if v > 0 else "-Infinity"
        return v.item() if hasattr(v, "item") else v

    records = [{c: clean(v) for c, v in row.items()} for row in df.to_dict("records")]
    return {"columns": list(df.columns), "rows": records}
