"""Alert queries and investigation-status updates."""
from __future__ import annotations

import json

from backend.app.core.config import MAX_PAGE_SIZE
from backend.app.core.errors import BadRequestError, NotFoundError
from backend.app.database.db import utcnow

STATUSES = ("new", "under_review", "resolved")
SEVERITIES = ("High", "Medium")
NOTE = "Predicted by the model. Not independently verified."


def list_alerts(db, page: int = 1, page_size: int = 25, status: str | None = None,
                severity: str | None = None, analysis_id: int | None = None) -> dict:
    if status not in (None, *STATUSES):
        raise BadRequestError(f"status must be one of: {', '.join(STATUSES)}.")
    if severity not in (None, *SEVERITIES):
        raise BadRequestError(f"severity must be one of: {', '.join(SEVERITIES)}.")
    page, page_size = max(1, page), max(1, min(page_size, MAX_PAGE_SIZE))
    where, args = [], []
    if status:
        where.append("a.status = ?"); args.append(status)
    if severity:
        where.append("a.severity = ?"); args.append(severity)
    if analysis_id is not None:
        where.append("a.analysis_id = ?"); args.append(analysis_id)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    total = db.execute(f"SELECT COUNT(*) FROM alerts a {where_sql}", args).fetchone()[0]
    rows = db.execute(
        "SELECT a.id, a.analysis_id, a.flow_id, a.created_at, a.updated_at, a.predicted_class, a.severity,"
        " a.confidence, a.status, f.flow_ref, f.destination_port, f.protocol, f.packets, f.bytes"
        f" FROM alerts a JOIN flows f ON f.id = a.flow_id {where_sql}"
        " ORDER BY CASE a.severity WHEN 'High' THEN 0 ELSE 1 END, a.id DESC LIMIT ? OFFSET ?",
        [*args, page_size, (page - 1) * page_size]).fetchall()
    counts = {r[0]: r[1] for r in db.execute("SELECT status, COUNT(*) FROM alerts GROUP BY status")}
    return {"items": [dict(r) for r in rows], "total": total, "page": page, "page_size": page_size,
            "status_counts": {s: counts.get(s, 0) for s in STATUSES}, "note": NOTE}


def get_alert(db, alert_id: int) -> dict:
    row = db.execute(
        "SELECT a.*, f.flow_ref, f.timestamp, f.protocol, f.destination_port, f.packets, f.bytes,"
        " f.features_json, f.actual_label, an.model_id, an.model_name, an.mode, an.is_synthetic "
        "FROM alerts a JOIN flows f ON f.id = a.flow_id JOIN analyses an ON an.id = a.analysis_id "
        "WHERE a.id = ?", (alert_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"Alert {alert_id} was not found.")
    d = dict(row)
    d["features"] = json.loads(d.pop("features_json"))
    d["is_synthetic"] = bool(d["is_synthetic"])
    d["note"] = NOTE
    return d


def update_status(db, alert_id: int, status: str) -> dict:
    if status not in STATUSES:
        raise BadRequestError(f"status must be one of: {', '.join(STATUSES)}.")
    cur = db.execute("UPDATE alerts SET status=?, updated_at=? WHERE id=?", (status, utcnow(), alert_id))
    if cur.rowcount == 0:
        raise NotFoundError(f"Alert {alert_id} was not found.")
    db.commit()
    return get_alert(db, alert_id)
