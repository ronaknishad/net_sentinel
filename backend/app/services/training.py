"""Background training jobs. One job at a time; progress is stored in SQLite."""
from __future__ import annotations

import threading
from pathlib import Path

from backend.app.core.errors import BadRequestError, ConflictError, NotFoundError
from backend.app.database.db import connect, rows_to_dicts, utcnow
from backend.app.services import datasets as dataset_service
from ml.preprocessing import DatasetError
from ml.train import train_and_evaluate

_lock = threading.Lock()
_active: threading.Thread | None = None


def _is_busy() -> bool:
    return _active is not None and _active.is_alive()


def start_training(db_path: Path, uploads_dir: Path, artifacts_dir: Path, dataset_id: int,
                   mode: str, confirm: bool, on_complete=None) -> dict:
    global _active
    if not confirm:
        raise BadRequestError("Training must be confirmed explicitly (confirm: true).")
    if mode not in ("binary", "multiclass"):
        raise BadRequestError("mode must be 'binary' or 'multiclass'.")
    conn = connect(db_path)
    try:
        ds = dataset_service.get_dataset(conn, dataset_id)
        if not ds["is_valid"]:
            raise BadRequestError("This dataset failed validation: " + " ".join(ds["validation"]["errors"]))
        with _lock:
            if _is_busy():
                raise ConflictError("A training job is already running.")
            cur = conn.execute("INSERT INTO training_runs (dataset_id, mode, status, started_at) "
                               "VALUES (?,?,'running',?)", (dataset_id, mode, utcnow()))
            conn.commit()
            run_id = cur.lastrowid
            _active = threading.Thread(
                target=_run, daemon=True,
                args=(db_path, uploads_dir, artifacts_dir, dataset_id, mode, run_id, on_complete))
            _active.start()
        return get_run(conn, run_id)
    finally:
        conn.close()


def _run(db_path, uploads_dir, artifacts_dir, dataset_id, mode, run_id, on_complete):
    conn = connect(db_path)
    try:
        df, ds = dataset_service.load_dataset_frame(conn, uploads_dir, dataset_id)
        ev = train_and_evaluate(df, ds["label_column"], mode, dataset_name=ds["name"],
                                is_synthetic=ds["is_synthetic"], artifacts_dir=artifacts_dir)
        conn.execute("UPDATE training_runs SET status='completed', finished_at=?, model_id=? WHERE id=?",
                     (utcnow(), ev["model_id"], run_id))
        conn.commit()
        if on_complete:
            on_complete()
    except DatasetError as exc:
        _fail(conn, run_id, str(exc))
    except Exception as exc:  # keep the job record accurate whatever went wrong
        _fail(conn, run_id, f"Training failed ({type(exc).__name__}): {exc}")
    finally:
        conn.close()


def _fail(conn, run_id, message):
    conn.execute("UPDATE training_runs SET status='failed', finished_at=?, error=? WHERE id=?",
                 (utcnow(), message, run_id))
    conn.commit()


def wait_for_active(timeout: float = 120) -> None:
    """Block until the current job ends (used by tests)."""
    if _active is not None:
        _active.join(timeout)


def get_run(db, run_id: int) -> dict:
    row = db.execute("SELECT * FROM training_runs WHERE id=?", (run_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"Training run {run_id} was not found.")
    return dict(row)


def list_runs(db, limit: int = 20) -> list[dict]:
    return rows_to_dicts(db.execute("SELECT * FROM training_runs ORDER BY id DESC LIMIT ?", (limit,)))
