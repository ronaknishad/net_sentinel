import json

from backend.app.core.errors import BadRequestError, ConflictError, NotFoundError
from backend.app.database.db import connect
from backend.app.services import alerts, analyses, datasets, exports, training
from backend.app.services import system as system_service
from backend.app.core.config import Settings
from backend.tests._helpers import Env, assert_raises
from ml.predict import Predictor, PredictionInputError


def _trained_env(mode="multiclass"):
    env = Env(); db = env.db()
    ds = datasets.register_bundled_sample(db, env.uploads)
    run = training.start_training(env.db_path, env.uploads, env.artifacts, ds["id"], mode, True)
    assert run["status"] == "running"
    training.wait_for_active()
    run = training.get_run(db, run["id"])
    assert run["status"] == "completed", run
    return env, db, ds, Predictor.load(env.artifacts)


def test_training_requires_confirmation_and_valid_dataset():
    env = Env(); db = env.db()
    ds = datasets.register_bundled_sample(db, env.uploads)
    with assert_raises(BadRequestError, "confirm"):
        training.start_training(env.db_path, env.uploads, env.artifacts, ds["id"], "binary", False)
    with assert_raises(BadRequestError, "mode"):
        training.start_training(env.db_path, env.uploads, env.artifacts, ds["id"], "weird", True)
    with assert_raises(NotFoundError):
        training.start_training(env.db_path, env.uploads, env.artifacts, 999, "binary", True)
    import io
    bad = datasets.save_upload(db, env.uploads, "bad.csv", io.BytesIO(b"x,y\n1,2\n"))
    with assert_raises(BadRequestError, "failed validation"):
        training.start_training(env.db_path, env.uploads, env.artifacts, bad["id"], "binary", True)


def test_training_job_runs_in_background_and_blocks_a_second_job():
    env = Env(); db = env.db()
    ds = datasets.register_bundled_sample(db, env.uploads)
    done = []
    run = training.start_training(env.db_path, env.uploads, env.artifacts, ds["id"], "multiclass", True,
                                  on_complete=lambda: done.append(1))
    with assert_raises(ConflictError, "already running"):
        training.start_training(env.db_path, env.uploads, env.artifacts, ds["id"], "binary", True)
    training.wait_for_active()
    assert done == [1] and training.get_run(db, run["id"])["model_id"]
    assert (env.artifacts / "evaluation.json").is_file()
    assert training.list_runs(db)[0]["status"] == "completed"


def test_full_workflow_dataset_analysis_flows_and_alerts():
    env, db, ds, predictor = _trained_env()
    a = analyses.analyse_dataset(db, env.uploads, predictor, ds["id"])
    assert a["total_flows"] + a["rejected_count"] == ds["row_count"]
    assert a["normal_count"] + a["suspicious_count"] == a["total_flows"]
    assert a["is_synthetic"] and any("synthetic" in w.lower() for w in a["warnings"])

    all_flows = analyses.list_flows(db, a["id"], page_size=50)
    assert all_flows["total"] == a["total_flows"] and len(all_flows["items"]) == 50
    sus = analyses.list_flows(db, a["id"], classification="suspicious", page_size=200)
    assert sus["total"] == a["suspicious_count"]
    assert all(f["is_suspicious"] and f["severity"] in ("High", "Medium") for f in sus["items"])

    # persisted alerts match suspicious predictions
    al = alerts.list_alerts(db, page_size=200, analysis_id=a["id"])
    assert al["total"] == a["suspicious_count"] and al["status_counts"]["new"] == al["total"]
    assert al["items"][0]["severity"] == "High"                     # High sorted first
    detail = alerts.get_alert(db, al["items"][0]["id"])
    assert detail["features"] and "not independently verified" in detail["note"].lower()
    assert detail["model_id"] == predictor.metadata["model_id"]


def test_flow_filters_sorting_search_and_pagination():
    env, db, ds, predictor = _trained_env()
    a = analyses.analyse_dataset(db, env.uploads, predictor, ds["id"])
    p1 = analyses.list_flows(db, a["id"], page=1, page_size=10, sort_by="confidence", sort_dir="desc")
    confs = [f["confidence"] for f in p1["items"]]
    assert confs == sorted(confs, reverse=True)
    p2 = analyses.list_flows(db, a["id"], page=2, page_size=10, sort_by="confidence", sort_dir="desc")
    assert {f["id"] for f in p1["items"]}.isdisjoint({f["id"] for f in p2["items"]})
    only_dos = analyses.list_flows(db, a["id"], attack_class="DoS", page_size=200)
    assert only_dos["total"] > 0 and {f["predicted_class"] for f in only_dos["items"]} == {"DoS"}
    tcp = analyses.list_flows(db, a["id"], protocol="TCP", page_size=200)
    assert tcp["total"] > 0 and all(f["protocol"] == "TCP" for f in tcp["items"])
    hi = analyses.list_flows(db, a["id"], min_confidence=0.95, page_size=200)
    assert all(f["confidence"] >= 0.95 for f in hi["items"])
    by_ref = analyses.list_flows(db, a["id"], search="SYN-000007")
    assert by_ref["total"] >= 1 and all("SYN-000007" in f["flow_ref"] for f in by_ref["items"])
    by_port = analyses.list_flows(db, a["id"], search="22", page_size=200)
    assert by_port["total"] > 0
    # hostile input is treated as data, never as SQL
    assert analyses.list_flows(db, a["id"], search="'; DROP TABLE flows;--")["total"] == 0
    assert analyses.list_flows(db, a["id"], search="%")["total"] == 0
    assert db.execute("SELECT COUNT(*) FROM flows").fetchone()[0] > 0
    for kwargs in ({"sort_by": "features_json"}, {"sort_dir": "sideways"}, {"classification": "weird"}):
        with assert_raises(BadRequestError):
            analyses.list_flows(db, a["id"], **kwargs)
    f = analyses.get_flow(db, p1["items"][0]["id"])
    assert f["features"]["destination_port"] is not None and f["model"]["model_name"]
    assert "DoS" in analyses.facets(db, a["id"])["classes"]


def test_alert_status_updates_persist_across_connections():
    env, db, ds, predictor = _trained_env()
    a = analyses.analyse_dataset(db, env.uploads, predictor, ds["id"])
    alert_id = alerts.list_alerts(db, analysis_id=a["id"])["items"][0]["id"]
    updated = alerts.update_status(db, alert_id, "under_review")
    assert updated["status"] == "under_review"
    db.close()
    fresh = connect(env.db_path)                                     # simulates an application restart
    assert alerts.get_alert(fresh, alert_id)["status"] == "under_review"
    assert alerts.list_alerts(fresh, status="under_review")["total"] == 1
    with assert_raises(BadRequestError, "status must be"):
        alerts.update_status(fresh, alert_id, "closed-ish")
    with assert_raises(NotFoundError):
        alerts.update_status(fresh, 99999, "resolved")
    with assert_raises(BadRequestError):
        alerts.list_alerts(fresh, severity="Critical")


def test_timeline_and_summary_use_real_timestamps():
    env, db, ds, predictor = _trained_env()
    a = analyses.analyse_dataset(db, env.uploads, predictor, ds["id"])
    s = analyses.analysis_summary(db, a["id"])
    assert sum(s["class_distribution"].values()) == a["total_flows"]
    tl = s["timeline"]
    assert tl["available"] and sum(b["normal"] + b["suspicious"] for b in tl["buckets"]) == a["total_flows"]
    assert sum(s["severity_distribution"].values()) == a["suspicious_count"]


def test_overview_empty_state_then_populated():
    env = Env(); db = env.db()
    o = analyses.overview(db, None, False)
    assert o == {**o, "has_analysis": False, "latest": None, "model_loaded": False,
                 "evaluation_available": False, "open_alerts": 0}
    env2, db2, ds, predictor = _trained_env()
    analyses.analyse_synthetic(db2, predictor, 200, 3)
    o2 = analyses.overview(db2, predictor, True)
    assert o2["has_analysis"] and o2["latest"]["analysis"]["source"] == "synthetic" and o2["open_alerts"] > 0


def test_single_record_prediction_and_saved_analysis():
    env, db, ds, predictor = _trained_env()
    samples = analyses.sample_records()
    assert {s["synthetic_label"] for s in samples} == {"Normal", "DoS", "PortScan", "Brute Force"}
    by_label = {s["synthetic_label"]: s["record"] for s in samples}
    assert predictor.predict_record(by_label["Normal"])["predicted_class"] == "Normal"
    assert predictor.predict_record(by_label["DoS"])["is_suspicious"] is True
    saved = analyses.analyse_record(db, predictor, by_label["PortScan"])
    assert saved["total_flows"] == 1 and saved["source"] == "record"
    with assert_raises(PredictionInputError):
        predictor.predict_record({"destination_port": 80})
    with assert_raises(BadRequestError, "between 10"):
        analyses.analyse_synthetic(db, predictor, 5, 1)


def test_unlabelled_csv_can_be_analysed():
    import io
    env, db, ds, predictor = _trained_env()
    from ml.synthetic import generate_synthetic_flows
    df = generate_synthetic_flows(300, seed=5).drop(columns=["Label"])
    u = datasets.save_upload(db, env.uploads, "unlabelled.csv", io.BytesIO(df.to_csv(index=False).encode()))
    a = analyses.analyse_dataset(db, env.uploads, predictor, u["id"])
    f = analyses.list_flows(db, a["id"], page_size=1)["items"][0]
    assert f["actual_label"] is None and a["total_flows"] > 250


def test_exports_evaluation_and_flows():
    env, db, ds, predictor = _trained_env()
    ev = exports.load_evaluation(env.artifacts)
    csv_text = exports.evaluation_csv(ev)
    lines = csv_text.splitlines()
    assert lines[0] == "section,model,class,metric,value" and any(l.startswith("comparison,Random Forest") for l in lines)
    assert any(l.startswith("confusion_matrix") for l in lines)
    a = analyses.analyse_synthetic(db, predictor, 100, 2)
    flows = exports.flows_csv(db, a["id"]).splitlines()
    assert flows[0].startswith("flow_ref,timestamp") and len(flows) == a["total_flows"] + 1
    with assert_raises(NotFoundError, "unavailable"):
        exports.load_evaluation(Env().artifacts)
    with assert_raises(NotFoundError):
        exports.flows_csv(db, 999)
    assert exports._safe("=HYPERLINK(\"x\")").startswith("'=") and exports._safe("normal") == "normal"


def test_system_info_reports_only_real_values():
    env, db, ds, predictor = _trained_env()
    s = Settings(data_dir=env.root, artifacts_dir=env.artifacts)
    info = system_service.system_info(s, predictor, None)
    assert info["model"]["loaded"] and info["datasets"]["file_count"] == 1
    assert info["live_capture"]["configured"] is False and len(info["input_schema"]["features"]) == 15
    empty = system_service.system_info(s, None, "No trained model found. Train a model first.")
    assert not empty["model"]["loaded"] and "Train" in empty["model"]["message"]
