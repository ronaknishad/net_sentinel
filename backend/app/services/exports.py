"""CSV / JSON exports. Text cells are neutralised against spreadsheet formula injection."""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from backend.app.core.errors import NotFoundError
from ml.config import EVALUATION_FILENAME


def _safe(value):
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


def load_evaluation(artifacts_dir: Path) -> dict:
    path = Path(artifacts_dir) / EVALUATION_FILENAME
    if not path.is_file():
        raise NotFoundError("Model evaluation is unavailable. Train a model first.")
    return json.loads(path.read_text(encoding="utf-8"))


def evaluation_csv(evaluation: dict) -> str:
    """Long-format table: section, model, class, metric, value."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["section", "model", "class", "metric", "value"])
    meta = {"model_id": evaluation["model_id"], "mode": evaluation["mode"],
            "dataset": evaluation["dataset_name"], "synthetic": evaluation["is_synthetic"],
            "train_samples": evaluation["split"]["train_samples"],
            "test_samples": evaluation["split"]["test_samples"]}
    for k, v in meta.items():
        w.writerow(["run", "", "", k, _safe(v)])
    for row in evaluation["model_comparison"]:
        for metric in ("accuracy", "precision", "recall", "f1", "normal_flagged_rate", "training_seconds"):
            w.writerow(["comparison", row["model"], "", metric, row[metric]])
    for model, m in evaluation["models"].items():
        for c in m["per_class"]:
            for metric in ("precision", "recall", "f1", "support", "false_positive_rate"):
                w.writerow(["per_class", model, _safe(c["class"]), metric, c[metric]])
        labels, matrix = m["confusion_matrix"]["labels"], m["confusion_matrix"]["matrix"]
        for i, actual in enumerate(labels):
            for j, predicted in enumerate(labels):
                w.writerow(["confusion_matrix", model, _safe(f"{actual} -> {predicted}"), "count", matrix[i][j]])
    return buf.getvalue()


def flows_csv(db, analysis_id: int) -> str:
    if db.execute("SELECT 1 FROM analyses WHERE id=?", (analysis_id,)).fetchone() is None:
        raise NotFoundError(f"Analysis {analysis_id} was not found.")
    rows = db.execute(
        "SELECT f.*, a.id AS alert_id, a.status AS alert_status FROM flows f "
        "LEFT JOIN alerts a ON a.flow_id = f.id WHERE f.analysis_id=? ORDER BY f.row_index", (analysis_id,)).fetchall()
    feature_names: list[str] = []
    parsed = []
    for r in rows:
        feats = json.loads(r["features_json"])
        for k in feats:
            if k not in feature_names:
                feature_names.append(k)
        parsed.append(feats)
    base = ["flow_ref", "timestamp", "protocol", "destination_port", "packets", "bytes", "predicted_class",
            "confidence", "severity", "actual_label", "alert_id", "alert_status"]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(base + feature_names)
    for r, feats in zip(rows, parsed):
        w.writerow([_safe(r[c]) for c in base] + [feats.get(k) for k in feature_names])
    return buf.getvalue()
