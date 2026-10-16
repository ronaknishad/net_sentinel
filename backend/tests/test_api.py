"""HTTP-level tests using FastAPI's TestClient.

These need `fastapi`, `httpx` and `pytest` (see backend/requirements.txt). They were written in a
sandbox without those packages, so they have NOT been executed yet; run them with
`python -m pytest backend\\tests -q` and fix anything they reveal.
"""
import io
import time

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from ml.config import DEFAULT_DATA_DIR

SAMPLE = DEFAULT_DATA_DIR / "sample_synthetic_flows.csv"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("NETSENTINEL_ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    with TestClient(app) as c:
        yield c


def _train(client, mode="multiclass"):
    ds = client.post("/api/datasets/sample").json()
    r = client.post("/api/models/train", json={"dataset_id": ds["id"], "mode": mode, "confirm": True})
    assert r.status_code == 202
    for _ in range(120):
        run = client.get(f"/api/models/train/{r.json()['id']}").json()
        if run["status"] != "running":
            break
        time.sleep(0.5)
    assert run["status"] == "completed", run
    return ds


def test_health_and_untrained_model_status(client):
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and h["model_loaded"] is False and h["live_capture"] == "not_implemented"
    s = client.get("/api/model/status").json()
    assert s["loaded"] is False and "Train" in s["message"]
    assert client.get("/api/models/evaluation").status_code == 404
    assert client.get("/api/exports/evaluation").status_code == 404


def test_upload_validation_errors(client):
    r = client.post("/api/datasets/upload", files={"file": ("x.exe", io.BytesIO(b"a,b\n1,2"), "text/csv")})
    assert r.status_code == 400
    r = client.post("/api/datasets/upload", files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")})
    assert r.status_code == 422
    assert client.get("/api/datasets/999").status_code == 404


def test_upload_preview_and_train_confirmation(client):
    with open(SAMPLE, "rb") as f:
        r = client.post("/api/datasets/upload", files={"file": ("flows.csv", f, "text/csv")},
                        data={"is_synthetic": "true"})
    assert r.status_code == 201 and r.json()["is_valid"]
    ds_id = r.json()["id"]
    assert len(client.get(f"/api/datasets/{ds_id}/preview?rows=5").json()["rows"]) == 5
    assert client.post("/api/models/train", json={"dataset_id": ds_id, "mode": "binary"}).status_code == 400
    assert client.post("/api/models/train", json={"dataset_id": ds_id, "mode": "x", "confirm": True}).status_code == 422


def test_predictions_need_a_model_and_valid_records(client):
    assert client.post("/api/predictions", json={"record": {"destination_port": 80}}).status_code == 409
    assert client.post("/api/analyses", json={"source": "synthetic"}).status_code == 409
    _train(client)
    assert client.get("/api/model/status").json()["loaded"] is True
    bad = client.post("/api/predictions", json={"record": {"destination_port": 80}})
    assert bad.status_code == 422 and "missing" in bad.json()["detail"].lower()
    sample = client.get("/api/predictions/samples").json()["items"][0]["record"]
    ok = client.post("/api/predictions", json={"record": sample}).json()
    assert ok["prediction"]["predicted_class"] and "not a calibrated" in ok["probability_note"]


def test_full_flow_alerts_and_exports(client):
    ds = _train(client)
    a = client.post("/api/analyses", json={"source": "dataset", "dataset_id": ds["id"]}).json()
    assert a["total_flows"] > 0
    flows = client.get(f"/api/flows?analysis_id={a['id']}&classification=suspicious&sort_by=confidence&sort_dir=desc").json()
    assert flows["total"] == a["suspicious_count"]
    assert client.get("/api/flows?sort_by=bogus").status_code == 400
    assert client.get("/api/flows?page_size=9999").status_code == 422
    alert = client.get(f"/api/alerts?analysis_id={a['id']}").json()["items"][0]
    patched = client.patch(f"/api/alerts/{alert['id']}", json={"status": "resolved"})
    assert patched.status_code == 200 and patched.json()["status"] == "resolved"
    assert client.patch(f"/api/alerts/{alert['id']}", json={"status": "bogus"}).status_code == 422
    assert client.patch("/api/alerts/99999", json={"status": "new"}).status_code == 404
    assert client.get("/api/exports/evaluation?format=csv").headers["content-type"].startswith("text/csv")
    assert client.get("/api/exports/evaluation?format=xml").status_code == 400
    assert client.get(f"/api/exports/analyses/{a['id']}").text.startswith("flow_ref,")
    assert client.get("/api/overview").json()["has_analysis"] is True
    assert client.get("/api/system/info").json()["live_capture"]["configured"] is False
