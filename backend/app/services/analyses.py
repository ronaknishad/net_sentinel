"""Running predictions over flow records, storing results, and querying them."""
from __future__ import annotations

import json
import re

import numpy as np
import pandas as pd

from backend.app.core.config import MAX_ANALYSIS_ROWS, MAX_PAGE_SIZE, MAX_SYNTHETIC_ROWS
from backend.app.core.errors import BadRequestError, NotFoundError
from backend.app.database.db import rows_to_dicts, utcnow
from backend.app.services import datasets as dataset_service
from ml.feature_schema import normalize_name
from ml.predict import Predictor
from ml.preprocessing import map_columns, normalize_labels
from ml.synthetic import generate_synthetic_flows

PROTOCOL_NAMES = {1: "ICMP", 6: "TCP", 17: "UDP"}
SORTABLE = {"row_index", "flow_ref", "timestamp", "protocol", "destination_port", "packets",
            "bytes", "predicted_class", "confidence", "severity"}


def _num(df: pd.DataFrame, mapping: dict, name: str):
    if name not in mapping:
        return None
    s = pd.to_numeric(df[mapping[name]], errors="coerce")
    return s.replace([np.inf, -np.inf], np.nan)


def _int_or_none(v):
    return None if v is None or pd.isna(v) else int(v)


def _warnings_for(predictor: Predictor, source_name: str, labelled: bool) -> list[str]:
    meta = predictor.metadata
    out = [f"The active model was trained on '{meta['dataset_name']}'. Predictions on unrelated "
           "datasets may be unreliable."]
    if meta["is_synthetic"]:
        out.append("The active model was trained on synthetic demonstration data. Results show how "
                   "the workflow behaves, not real-world detection performance.")
    out.append("Classifications are model predictions and have not been independently verified.")
    return out


def run_analysis(db, predictor: Predictor, df: pd.DataFrame, name: str, source: str,
                 dataset_id: int | None = None, is_synthetic_input: bool = False) -> dict:
    if len(df) > MAX_ANALYSIS_ROWS:
        raise BadRequestError(f"This analysis has {len(df):,} rows; the limit is {MAX_ANALYSIS_ROWS:,}.")
    output = predictor.predict_dataframe(df)
    results, rejected = output["results"], output["rejected"]
    if not results:
        raise BadRequestError("No rows could be classified: none had valid numeric feature values.")

    mapping, _ = map_columns(df.columns)
    norm = {normalize_name(c): c for c in df.columns}
    flow_col, ts_col = norm.get("flow_id"), norm.get("timestamp")
    label_col = next((norm[k] for k in ("label", "attack", "attack_cat", "class") if k in norm), None)

    X = pd.DataFrame({f: _num(df, mapping, f) for f in predictor.feature_names})
    protocol = _num(df, mapping, "protocol")
    dport = _num(df, mapping, "destination_port")
    fwd, bwd = _num(df, mapping, "total_fwd_packets"), _num(df, mapping, "total_bwd_packets")
    fb, bb = _num(df, mapping, "total_fwd_bytes"), _num(df, mapping, "total_bwd_bytes")
    packets = (fwd + bwd) if fwd is not None and bwd is not None else None
    nbytes = (fb + bb) if fb is not None and bb is not None else None
    timestamps = pd.to_datetime(df[ts_col], errors="coerce") if ts_col else None
    actual = normalize_labels(df[label_col]) if label_col else None

    suspicious = [r for r in results if r["is_suspicious"]]
    high = sum(1 for r in suspicious if r["severity"] == "High")
    meta = predictor.metadata
    warnings = _warnings_for(predictor, name, label_col is not None)
    if is_synthetic_input:
        warnings.insert(0, "The input records are synthetic. This run demonstrates the workflow only.")

    cur = db.execute(
        "INSERT INTO analyses (name, source, dataset_id, model_id, model_name, mode, is_synthetic,"
        " total_flows, normal_count, suspicious_count, high_severity_count, rejected_count,"
        " warnings_json, rejected_json, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (name, source, dataset_id, meta["model_id"], meta["model_name"], meta["mode"],
         int(meta["is_synthetic"] or is_synthetic_input), len(results), len(results) - len(suspicious),
         len(suspicious), high, len(rejected), json.dumps(warnings), json.dumps(rejected[:100]), utcnow()))
    analysis_id = cur.lastrowid

    flow_rows = []
    for r in results:
        i = r["row_index"]
        ts = timestamps.iloc[i] if timestamps is not None else None
        feats = {k: (None if pd.isna(v) else float(v)) for k, v in X.iloc[i].items()}
        flow_rows.append((
            analysis_id, i,
            str(df[flow_col].iloc[i]) if flow_col else f"row-{i}",
            None if ts is None or pd.isna(ts) else ts.isoformat(),
            None if protocol is None or pd.isna(protocol.iloc[i]) else
            PROTOCOL_NAMES.get(int(protocol.iloc[i]), str(int(protocol.iloc[i]))),
            _int_or_none(dport.iloc[i]) if dport is not None else None,
            _int_or_none(packets.iloc[i]) if packets is not None else None,
            _int_or_none(nbytes.iloc[i]) if nbytes is not None else None,
            r["predicted_class"], int(r["is_suspicious"]), r["confidence"], r["severity"],
            None if actual is None or pd.isna(actual.iloc[i]) else str(actual.iloc[i]),
            json.dumps(feats)))
    db.executemany(
        "INSERT INTO flows (analysis_id, row_index, flow_ref, timestamp, protocol, destination_port,"
        " packets, bytes, predicted_class, is_suspicious, confidence, severity, actual_label,"
        " features_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", flow_rows)

    now = utcnow()
    sus = db.execute("SELECT id, predicted_class, severity, confidence FROM flows "
                     "WHERE analysis_id=? AND is_suspicious=1", (analysis_id,)).fetchall()
    db.executemany(
        "INSERT INTO alerts (analysis_id, flow_id, created_at, updated_at, predicted_class, severity,"
        " confidence, status) VALUES (?,?,?,?,?,?,?, 'new')",
        [(analysis_id, f["id"], now, now, f["predicted_class"], f["severity"], f["confidence"]) for f in sus])
    db.commit()
    return get_analysis(db, analysis_id)


def analyse_dataset(db, uploads_dir, predictor: Predictor, dataset_id: int) -> dict:
    df, ds = dataset_service.load_dataset_frame(db, uploads_dir, dataset_id)
    return run_analysis(db, predictor, df, ds["name"], "dataset", dataset_id,
                        is_synthetic_input=ds["is_synthetic"])


def analyse_synthetic(db, predictor: Predictor, rows: int, seed: int) -> dict:
    if not 10 <= rows <= MAX_SYNTHETIC_ROWS:
        raise BadRequestError(f"Synthetic row count must be between 10 and {MAX_SYNTHETIC_ROWS}.")
    df = generate_synthetic_flows(rows, seed)
    return run_analysis(db, predictor, df, f"Synthetic demonstration ({rows} flows, seed {seed})",
                        "synthetic", None, is_synthetic_input=True)


def analyse_record(db, predictor: Predictor, record: dict) -> dict:
    df = pd.DataFrame([record])
    return run_analysis(db, predictor, df, "Single record", "record", None)


def sample_records(predictor: Predictor | None = None) -> list[dict]:
    """One SYNTHETIC example per class, expressed in the model's input schema."""
    df = generate_synthetic_flows(400, seed=1)
    mapping, _ = map_columns(df.columns)
    out, seen = [], set()
    for _, row in df.iterrows():
        label = row["Label"]
        if label in seen:
            continue
        rec = {f: (None if pd.isna(row[c]) or np.isinf(row[c]) else float(row[c])) for f, c in mapping.items()}
        if any(v is None for v in rec.values()):
            continue
        seen.add(label)
        out.append({"synthetic_label": "Normal" if label == "BENIGN" else label, "record": rec,
                    "note": "Synthetic example generated by documented rules."})
        if len(seen) == 4:
            break
    return out


# ----------------------------------------------------------------------------- queries
def _analysis(row) -> dict:
    d = dict(row)
    d["warnings"] = json.loads(d.pop("warnings_json"))
    d["rejected"] = json.loads(d.pop("rejected_json"))
    d["is_synthetic"] = bool(d["is_synthetic"])
    return d


def get_analysis(db, analysis_id: int) -> dict:
    row = db.execute("SELECT * FROM analyses WHERE id=?", (analysis_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"Analysis {analysis_id} was not found.")
    return _analysis(row)


def list_analyses(db, page: int = 1, page_size: int = 20) -> dict:
    page, page_size = max(1, page), max(1, min(page_size, MAX_PAGE_SIZE))
    total = db.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
    rows = db.execute("SELECT * FROM analyses ORDER BY id DESC LIMIT ? OFFSET ?",
                      (page_size, (page - 1) * page_size)).fetchall()
    return {"items": [_analysis(r) for r in rows], "total": total, "page": page, "page_size": page_size}


def _escape_like(s: str) -> str:
    return re.sub(r"([\\%_])", r"\\\1", s)


def list_flows(db, analysis_id: int | None = None, page: int = 1, page_size: int = 25,
               search: str | None = None, classification: str | None = None,
               attack_class: str | None = None, protocol: str | None = None,
               min_confidence: float | None = None, max_confidence: float | None = None,
               sort_by: str = "row_index", sort_dir: str = "asc") -> dict:
    if sort_by not in SORTABLE:
        raise BadRequestError(f"Cannot sort by '{sort_by}'.")
    if sort_dir not in ("asc", "desc"):
        raise BadRequestError("sort_dir must be 'asc' or 'desc'.")
    if classification not in (None, "normal", "suspicious"):
        raise BadRequestError("classification must be 'normal' or 'suspicious'.")
    page, page_size = max(1, page), max(1, min(page_size, MAX_PAGE_SIZE))

    where, args = [], []
    if analysis_id is not None:
        where.append("analysis_id = ?"); args.append(analysis_id)
    if classification:
        where.append("is_suspicious = ?"); args.append(1 if classification == "suspicious" else 0)
    if attack_class:
        where.append("predicted_class = ?"); args.append(attack_class)
    if protocol:
        where.append("protocol = ?"); args.append(protocol)
    if min_confidence is not None:
        where.append("confidence >= ?"); args.append(min_confidence)
    if max_confidence is not None:
        where.append("confidence <= ?"); args.append(max_confidence)
    if search:
        clause = "flow_ref LIKE ? ESCAPE '\\'"
        args.append(f"%{_escape_like(search.strip())}%")
        if search.strip().isdigit():
            clause = f"({clause} OR destination_port = ?)"; args.append(int(search.strip()))
        where.append(clause)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    total = db.execute(f"SELECT COUNT(*) FROM flows {where_sql}", args).fetchone()[0]
    order = f"{sort_by} {sort_dir.upper()}, id ASC"          # sort_by is whitelisted above
    rows = db.execute(
        "SELECT id, analysis_id, row_index, flow_ref, timestamp, protocol, destination_port, packets, bytes,"
        f" predicted_class, is_suspicious, confidence, severity, actual_label FROM flows {where_sql}"
        f" ORDER BY {order} LIMIT ? OFFSET ?", [*args, page_size, (page - 1) * page_size]).fetchall()
    items = [{**dict(r), "is_suspicious": bool(r["is_suspicious"])} for r in rows]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def get_flow(db, flow_id: int) -> dict:
    row = db.execute("SELECT * FROM flows WHERE id=?", (flow_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"Flow {flow_id} was not found.")
    d = dict(row)
    d["features"] = json.loads(d.pop("features_json"))
    d["is_suspicious"] = bool(d["is_suspicious"])
    analysis = get_analysis(db, d["analysis_id"])
    d["model"] = {"model_id": analysis["model_id"], "model_name": analysis["model_name"],
                  "mode": analysis["mode"], "is_synthetic": analysis["is_synthetic"]}
    alert = db.execute("SELECT id, status, severity, created_at FROM alerts WHERE flow_id=?", (flow_id,)).fetchone()
    d["alert"] = dict(alert) if alert else None
    return d


def facets(db, analysis_id: int | None = None) -> dict:
    """Distinct values for filter dropdowns (taken from stored data)."""
    where, args = ("WHERE analysis_id = ?", [analysis_id]) if analysis_id is not None else ("", [])
    classes = [r[0] for r in db.execute(f"SELECT DISTINCT predicted_class FROM flows {where} ORDER BY 1", args)]
    protos = [r[0] for r in db.execute(
        f"SELECT DISTINCT protocol FROM flows {where} {'AND' if where else 'WHERE'} protocol IS NOT NULL ORDER BY 1", args)]
    return {"classes": classes, "protocols": protos}


def analysis_summary(db, analysis_id: int) -> dict:
    analysis = get_analysis(db, analysis_id)
    dist = {r[0]: r[1] for r in db.execute(
        "SELECT predicted_class, COUNT(*) FROM flows WHERE analysis_id=? GROUP BY predicted_class ORDER BY 2 DESC",
        (analysis_id,))}
    sev = {r[0]: r[1] for r in db.execute(
        "SELECT severity, COUNT(*) FROM flows WHERE analysis_id=? AND is_suspicious=1 GROUP BY severity",
        (analysis_id,))}
    return {"analysis": analysis, "class_distribution": dist, "severity_distribution": sev,
            "timeline": _timeline(db, analysis_id, analysis["total_flows"])}


def _timeline(db, analysis_id: int, total: int) -> dict:
    rows = db.execute("SELECT timestamp, is_suspicious FROM flows WHERE analysis_id=? AND timestamp IS NOT NULL",
                      (analysis_id,)).fetchall()
    if len(rows) < max(20, 0.9 * total):
        return {"available": False, "reason": "Most flows in this analysis have no usable timestamp.", "buckets": []}
    df = pd.DataFrame(rows, columns=["timestamp", "is_suspicious"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna()
    span = df["timestamp"].max() - df["timestamp"].min()
    if span <= pd.Timedelta(0):
        return {"available": False, "reason": "All timestamps are identical.", "buckets": []}
    freq = next((f for f in ("1min", "5min", "15min", "1h", "6h", "1D") if span / pd.Timedelta(f) <= 200), "1D")
    df["bucket"] = df["timestamp"].dt.floor(freq)
    grouped = df.groupby("bucket")["is_suspicious"].agg(["count", "sum"])
    buckets = [{"bucket": b.isoformat(), "normal": int(r["count"] - r["sum"]), "suspicious": int(r["sum"])}
               for b, r in grouped.iterrows()]
    return {"available": True, "bucket_size": freq, "buckets": buckets}


def overview(db, predictor: Predictor | None, evaluation_available: bool) -> dict:
    row = db.execute("SELECT id FROM analyses ORDER BY id DESC LIMIT 1").fetchone()
    return {
        "has_analysis": row is not None,
        "latest": analysis_summary(db, row["id"]) if row else None,
        "model": predictor.metadata if predictor else None,
        "model_loaded": predictor is not None,
        "evaluation_available": evaluation_available,
        "open_alerts": db.execute("SELECT COUNT(*) FROM alerts WHERE status != 'resolved'").fetchone()[0],
        "analyses_total": db.execute("SELECT COUNT(*) FROM analyses").fetchone()[0],
    }
