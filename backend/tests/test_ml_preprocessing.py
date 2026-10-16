import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from backend.tests._helpers import assert_raises, small_dataset
from ml.preprocessing import (DatasetError, clean_dataset, load_csv, map_columns,
                              normalize_labels, to_binary, validate_dataframe)


def _write(text, name="data.csv"):
    d = tempfile.mkdtemp()
    p = Path(d) / name
    p.write_text(text, encoding="utf-8")
    return p


def test_load_csv_strips_header_whitespace():
    p = _write(" Destination Port , Label \n80,BENIGN\n")
    df = load_csv(p)
    assert list(df.columns) == ["Destination Port", "Label"]


def test_load_csv_rejects_bad_files():
    with assert_raises(DatasetError, "only .csv"):
        load_csv(_write("a,b\n1,2\n", "data.txt"))
    with assert_raises(DatasetError, "empty"):
        load_csv(_write("", "empty.csv"))
    with assert_raises(DatasetError, "no data rows"):
        load_csv(_write("a,b\n", "header.csv"))
    with assert_raises(DatasetError, "limit"):
        load_csv(_write("a,b\n1,2\n"), max_bytes=3)
    with assert_raises(DatasetError, "more than"):
        load_csv(_write("a\n1\n2\n3\n"), max_rows=2)
    with assert_raises(DatasetError, "not found"):
        load_csv(Path(tempfile.mkdtemp()) / "missing.csv")


def test_column_mapping_handles_cic_variants_and_excludes_identifiers():
    mapping, unsupported = map_columns(
        ["Tot Fwd Pkts", "Flow Byts/s", " Destination Port", "Flow ID", "Source IP", "Weird Col"])
    assert mapping["total_fwd_packets"] == "Tot Fwd Pkts"
    assert mapping["flow_bytes_per_s"] == "Flow Byts/s"
    assert mapping["destination_port"] == " Destination Port"
    reasons = {u["column"]: u["reason"] for u in unsupported}
    assert "Identifier" in reasons["Flow ID"] and "IP" in reasons["Source IP"]
    assert reasons["Weird Col"].startswith("Not part")


def test_validation_reports_missing_infinite_duplicates_and_classes():
    df = small_dataset()
    report = validate_dataframe(df)
    assert report.is_valid and report.label_column == "Label"
    assert report.duplicate_rows > 0
    assert report.infinite_values.get("flow_bytes_per_s", 0) > 0
    assert report.missing_values.get("flow_iat_mean", 0) > 0
    assert "Normal" in report.class_distribution and "BENIGN" not in report.class_distribution
    assert any(u["column"] == "Flow ID" for u in report.unsupported_columns)


def test_validation_errors_are_reported_not_silent():
    no_label = pd.DataFrame({"Destination Port": [80], "Flow Duration": [10]})
    r = validate_dataframe(no_label)
    assert not r.is_valid and any("label" in e.lower() for e in r.errors)
    r2 = validate_dataframe(small_dataset(), label_column="Nope")
    assert any("not found" in e for e in r2.errors)
    r3 = validate_dataframe(pd.DataFrame({"Label": ["a"], "x": [1]}))
    assert any("schema features" in e for e in r3.errors)


def test_cleaning_counts_rows_and_replaces_infinite_values():
    df = small_dataset()
    report = validate_dataframe(df)
    cleaned = clean_dataset(df, report.mapped_features, report.label_column)
    s = cleaned.stats
    assert s["rows_before"] == len(df)
    assert s["rows_after"] == len(cleaned.X) == len(cleaned.y)
    assert s["rows_before"] - s["rows_after"] == (
        s["dropped_missing_label"] + s["dropped_no_valid_features"] + s["dropped_duplicates"])
    assert s["dropped_duplicates"] > 0
    assert not np.isinf(cleaned.X.to_numpy(dtype=float)).any()
    assert s["infinite_values_replaced"] > 0


def test_label_encoding_is_consistent():
    s = pd.Series(["BENIGN", "benign ", "Normal", "Web Attack \ufffd Brute Force", "", None, "DoS"])
    out = normalize_labels(s)
    assert list(out.iloc[:3]) == ["Normal"] * 3
    assert out.iloc[3] == "Web Attack - Brute Force"
    assert out.iloc[4] is pd.NA and out.iloc[5] is pd.NA
    assert list(to_binary(pd.Series(["Normal", "DoS", "PortScan"]))) == ["Normal", "Suspicious", "Suspicious"]
