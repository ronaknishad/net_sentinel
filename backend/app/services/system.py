"""System information for the Settings page. Only real, checkable values are reported."""
from __future__ import annotations

from pathlib import Path

from backend.app.core.config import APP_NAME, APP_VERSION, Settings
from ml.config import EVALUATION_FILENAME
from ml.feature_schema import FEATURES, SCHEMA_VERSION
from ml.predict import Predictor
from ml.severity import SEVERITY_POLICY


def system_info(settings: Settings, predictor: Predictor | None, model_error: str | None) -> dict:
    uploads = settings.uploads_dir
    files = [p for p in uploads.glob("*.csv")] if uploads.is_dir() else []
    db = settings.db_path
    return {
        "app": {"name": APP_NAME, "version": APP_VERSION},
        "backend": {"status": "ok"},
        "model": {"loaded": predictor is not None, "message": "Model loaded successfully." if predictor
                  else (model_error or "No trained model found. Train a model first."),
                  "metadata": predictor.metadata if predictor else None,
                  "evaluation_available": (settings.artifacts_dir / EVALUATION_FILENAME).is_file()},
        "datasets": {"directory": str(uploads), "file_count": len(files),
                     "total_bytes": sum(p.stat().st_size for p in files)},
        "storage": {"database_path": str(db), "database_exists": db.is_file(),
                    "database_bytes": db.stat().st_size if db.is_file() else 0},
        "input_schema": {"version": SCHEMA_VERSION,
                         "features": [{"name": f.name, "description": f.description,
                                       "accepted_headers": list(f.aliases)} for f in FEATURES]},
        "severity_policy": SEVERITY_POLICY,
        "live_capture": {"configured": False, "message": "Live network capture is not configured."},
    }
