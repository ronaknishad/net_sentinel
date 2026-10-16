"""SQLite access (standard library). Uses parameterised queries only."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS datasets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    stored_name TEXT NOT NULL UNIQUE,
    size_bytes INTEGER NOT NULL,
    row_count INTEGER NOT NULL,
    columns_json TEXT NOT NULL,
    label_column TEXT,
    column_overrides_json TEXT NOT NULL DEFAULT '{}',
    is_synthetic INTEGER NOT NULL DEFAULT 0,
    is_valid INTEGER NOT NULL,
    validation_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS training_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id INTEGER NOT NULL REFERENCES datasets(id),
    mode TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    model_id TEXT,
    error TEXT
);
CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    source TEXT NOT NULL,
    dataset_id INTEGER REFERENCES datasets(id),
    model_id TEXT NOT NULL,
    model_name TEXT NOT NULL,
    mode TEXT NOT NULL,
    is_synthetic INTEGER NOT NULL,
    total_flows INTEGER NOT NULL,
    normal_count INTEGER NOT NULL,
    suspicious_count INTEGER NOT NULL,
    high_severity_count INTEGER NOT NULL,
    rejected_count INTEGER NOT NULL,
    warnings_json TEXT NOT NULL,
    rejected_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS flows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    row_index INTEGER NOT NULL,
    flow_ref TEXT NOT NULL,
    timestamp TEXT,
    protocol TEXT,
    destination_port INTEGER,
    packets INTEGER,
    bytes INTEGER,
    predicted_class TEXT NOT NULL,
    is_suspicious INTEGER NOT NULL,
    confidence REAL,
    severity TEXT NOT NULL,
    actual_label TEXT,
    features_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_flows_analysis ON flows(analysis_id, row_index);
CREATE INDEX IF NOT EXISTS idx_flows_class ON flows(analysis_id, predicted_class);
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    flow_id INTEGER NOT NULL REFERENCES flows(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    predicted_class TEXT NOT NULL,
    severity TEXT NOT NULL,
    confidence REAL,
    status TEXT NOT NULL DEFAULT 'new'
);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status, severity);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(db_path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.execute("UPDATE training_runs SET status='failed', finished_at=?, "
                     "error='Interrupted by an application restart.' WHERE status='running'",
                     (utcnow(),))
        conn.commit()
    finally:
        conn.close()


def rows_to_dicts(rows) -> list[dict]:
    return [dict(r) for r in rows]
