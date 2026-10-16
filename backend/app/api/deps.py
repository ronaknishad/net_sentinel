from fastapi import Request

from backend.app.core.config import Settings, get_settings
from backend.app.core.errors import ConflictError
from backend.app.database.db import connect


def get_db():
    conn = connect(get_settings().db_path)
    try:
        yield conn
    finally:
        conn.close()


def settings_dep() -> Settings:
    return get_settings()


def require_predictor(request: Request):
    predictor = request.app.state.predictor
    if predictor is None:
        raise ConflictError("No trained model is loaded. Train a model first.")
    return predictor
