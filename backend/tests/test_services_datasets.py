import io

import pandas as pd

from backend.app.core.errors import BadRequestError, NotFoundError, PayloadTooLargeError
from backend.app.services import datasets
from backend.tests._helpers import Env, assert_raises, csv_bytes, small_dataset
from ml.preprocessing import DatasetError


def test_upload_validates_and_stores_metadata():
    env, db = Env(), None
    db = env.db()
    ds = datasets.save_upload(db, env.uploads, "flows.csv", csv_bytes(small_dataset()))
    assert ds["is_valid"] and ds["row_count"] > 1000 and ds["label_column"] == "Label"
    assert ds["validation"]["class_distribution"]["Normal"] > 0
    assert "stored_name" not in ds                       # server-side file name is never exposed
    assert datasets.list_datasets(db)[0]["id"] == ds["id"]


def test_upload_rejects_bad_files_and_cleans_up():
    env = Env(); db = env.db()
    with assert_raises(BadRequestError, "only .csv"):
        datasets.save_upload(db, env.uploads, "evil.exe", io.BytesIO(b"a,b\n1,2\n"))
    with assert_raises(PayloadTooLargeError, "limit"):
        datasets.save_upload(db, env.uploads, "big.csv", csv_bytes(small_dataset()), max_bytes=1000)
    with assert_raises(DatasetError, "empty"):
        datasets.save_upload(db, env.uploads, "empty.csv", io.BytesIO(b""))
    assert list(env.uploads.glob("*")) == []             # nothing left behind
    assert datasets.list_datasets(db) == []


def test_filename_cannot_escape_upload_directory():
    env = Env(); db = env.db()
    datasets.save_upload(db, env.uploads, "../../outside.csv", csv_bytes(small_dataset(200)))
    assert not (env.root / "outside.csv").exists()
    assert len(list(env.uploads.glob("*.csv"))) == 1


def test_dataset_failing_validation_is_kept_with_its_errors():
    env = Env(); db = env.db()
    ds = datasets.save_upload(db, env.uploads, "nolabel.csv", io.BytesIO(b"Destination Port,Flow Duration\n80,10\n"))
    assert not ds["is_valid"] and ds["validation"]["errors"]


def test_preview_is_json_safe_and_limited():
    env = Env(); db = env.db()
    df = small_dataset(300)
    df.loc[0, "Flow Bytes/s"] = float("inf")
    ds = datasets.save_upload(db, env.uploads, "f.csv", csv_bytes(df))
    p = datasets.preview(db, env.uploads, ds["id"], rows=5)
    assert len(p["rows"]) == 5 and "Label" in p["columns"]
    assert p["rows"][0]["Flow Bytes/s"] == "Infinity"
    with assert_raises(NotFoundError):
        datasets.preview(db, env.uploads, 999)


def test_explicit_column_overrides_fix_unknown_headers():
    env = Env(); db = env.db()
    df = small_dataset(600).rename(columns={"Destination Port": "dport", "Flow Duration": "dur_us"})
    ds = datasets.save_upload(db, env.uploads, "custom.csv", csv_bytes(df))
    assert "destination_port" in ds["validation"]["missing_features"]
    ds = datasets.revalidate(db, env.uploads, ds["id"], None,
                             {"destination_port": "dport", "flow_duration": "dur_us"})
    assert "destination_port" not in ds["validation"]["missing_features"]
    frame, _ = datasets.load_dataset_frame(db, env.uploads, ds["id"])
    assert "destination_port" in frame.columns
    with assert_raises(BadRequestError, "does not exist"):
        datasets.revalidate(db, env.uploads, ds["id"], None, {"destination_port": "nope"})
    with assert_raises(BadRequestError, "not a supported feature"):
        datasets.revalidate(db, env.uploads, ds["id"], None, {"bogus": "dport"})


def test_revalidate_with_label_column_selection():
    env = Env(); db = env.db()
    df = small_dataset(500).rename(columns={"Label": "traffic_kind_x"})
    ds = datasets.save_upload(db, env.uploads, "l.csv", csv_bytes(df))
    assert not ds["is_valid"]
    ds = datasets.revalidate(db, env.uploads, ds["id"], "traffic_kind_x", None)
    assert ds["is_valid"] and ds["label_column"] == "traffic_kind_x"


def test_bundled_sample_is_registered_as_synthetic():
    env = Env(); db = env.db()
    ds = datasets.register_bundled_sample(db, env.uploads)
    assert ds["is_synthetic"] and ds["is_valid"] and "synthetic" in ds["name"]
