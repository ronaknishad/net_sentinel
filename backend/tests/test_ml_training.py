import tempfile

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer

from backend.tests._helpers import assert_raises, small_dataset
from ml.evaluate import compute_metrics
from ml.predict import ModelNotTrainedError, PredictionInputError, Predictor
from ml.preprocessing import DatasetError
from ml.severity import severity_for
from ml.synthetic import generate_synthetic_flows
from ml.train import build_pipeline, split_data, train_and_evaluate


def test_split_is_disjoint_stratified_and_reproducible():
    y = pd.Series(["Normal"] * 80 + ["DoS"] * 20)
    tr, te = split_data(y, 0.25, seed=1)
    assert set(tr).isdisjoint(te) and len(tr) + len(te) == 100
    assert abs((y.iloc[te] == "DoS").mean() - 0.20) < 0.05
    tr2, te2 = split_data(y, 0.25, seed=1)
    assert (tr == tr2).all() and (te == te2).all()


def test_imputer_learns_from_training_rows_only():
    X_train = pd.DataFrame({"a": [1.0, 2.0, 3.0, np.nan]})
    pipe = build_pipeline("Random Forest")
    imputer = pipe.named_steps["imputer"]
    assert isinstance(imputer, SimpleImputer)
    imputer.fit(X_train)
    assert imputer.statistics_[0] == 2.0   # median of training values, test outliers never seen


def test_metrics_match_hand_calculation():
    y_true = ["Normal"] * 6 + ["DoS"] * 4
    y_pred = ["Normal"] * 5 + ["DoS"] + ["DoS"] * 3 + ["Normal"]
    m = compute_metrics(y_true, y_pred, ["Normal", "DoS"], "multiclass")
    assert m["accuracy"] == 0.8
    assert m["confusion_matrix"]["matrix"] == [[5, 1], [1, 3]]
    assert abs(m["normal_flagged_rate"] - 1 / 6) < 1e-9
    dos = [c for c in m["per_class"] if c["class"] == "DoS"][0]
    assert abs(dos["precision"] - 0.75) < 1e-9 and abs(dos["recall"] - 0.75) < 1e-9
    assert abs(dos["false_positive_rate"] - 1 / 6) < 1e-9


def test_training_multiclass_and_binary_results_are_consistent():
    df = small_dataset()
    for mode, expected in (("multiclass", 4), ("binary", 2)):
        ev = train_and_evaluate(df, mode=mode, save=False, dataset_name="test", is_synthetic=True)
        assert len(ev["classes"]) == expected and len(ev["model_comparison"]) >= 2
        assert ev["is_synthetic"] and "Synthetic" in ev["provenance_note"]
        sel = ev["models"][ev["selected_model"]]
        assert sum(map(sum, sel["confusion_matrix"]["matrix"])) == ev["split"]["test_samples"]
        assert 0 <= sel["accuracy"] <= 1 and sel["training_seconds"] >= 0
        total = ev["split"]["train_samples"] + ev["split"]["test_samples"]
        assert total == ev["preprocessing"]["rows_after"]


def test_training_is_reproducible_with_fixed_seed():
    df = small_dataset()
    a = train_and_evaluate(df, mode="multiclass", save=False, seed=5)
    b = train_and_evaluate(df, mode="multiclass", save=False, seed=5)
    assert a["models"]["Random Forest"]["accuracy"] == b["models"]["Random Forest"]["accuracy"]
    assert a["models"]["Random Forest"]["confusion_matrix"] == b["models"]["Random Forest"]["confusion_matrix"]


def test_training_rejects_invalid_data():
    with assert_raises(DatasetError, "validation failed"):
        train_and_evaluate(pd.DataFrame({"x": [1, 2]}), mode="multiclass", save=False)
    benign_only = small_dataset()
    benign_only = benign_only[benign_only["Label"] == "BENIGN"]
    with assert_raises(DatasetError, "two classes"):
        train_and_evaluate(benign_only, mode="multiclass", save=False)
    with assert_raises(ValueError, "mode"):
        train_and_evaluate(small_dataset(), mode="weird", save=False)


def test_rare_classes_are_dropped_and_reported():
    df = small_dataset()
    rare = df[df["Label"] == "DoS"].head(3).copy()
    rare["Label"] = "Heartbleed"
    ev = train_and_evaluate(pd.concat([df, rare]), mode="multiclass", save=False)
    assert "Heartbleed" in ev["dropped_classes"] and "Heartbleed" not in ev["classes"]


def test_model_persistence_and_prediction_output_format():
    df = small_dataset()
    d = tempfile.mkdtemp()
    ev = train_and_evaluate(df, mode="multiclass", artifacts_dir=d, dataset_name="test", is_synthetic=True)
    p1, p2 = Predictor.load(d), Predictor.load(d)
    assert p1.metadata["model_id"] == ev["model_id"] and p1.metadata["is_synthetic"] is True
    sample = df.head(20)
    out1, out2 = p1.predict_dataframe(sample), p2.predict_dataframe(sample)
    assert out1 == out2 and len(out1["results"]) == 20
    r = out1["results"][0]
    assert {"row_index", "predicted_class", "is_suspicious", "severity", "confidence",
            "probabilities", "imputed_features"} <= set(r)
    assert 0 <= r["confidence"] <= 1 and r["predicted_class"] in ev["classes"]
    assert (r["severity"] == "None") == (not r["is_suspicious"])


def test_prediction_on_labelled_synthetic_rows_is_better_than_chance():
    df = generate_synthetic_flows(n=1500, seed=3)
    d = tempfile.mkdtemp()
    train_and_evaluate(small_dataset(), mode="multiclass", artifacts_dir=d)
    res = Predictor.load(d).predict_dataframe(df.head(300))["results"]
    truth = df.head(300)["Label"].replace({"BENIGN": "Normal"}).to_numpy()
    acc = np.mean([r["predicted_class"] == truth[r["row_index"]] for r in res])
    assert acc > 0.8


def test_invalid_prediction_requests_are_rejected():
    d = tempfile.mkdtemp()
    with assert_raises(ModelNotTrainedError, "train"):
        Predictor.load(d)
    train_and_evaluate(small_dataset(), mode="multiclass", artifacts_dir=d)
    pred = Predictor.load(d)
    with assert_raises(PredictionInputError, "missing required"):
        pred.predict_dataframe(pd.DataFrame({"Destination Port": [80]}))
    with assert_raises(PredictionInputError, "missing"):
        pred.predict_record({"Destination Port": 80})
    record = {f: 1.0 for f in pred.feature_names}
    assert pred.predict_record(record)["predicted_class"]
    for bad in ("abc", float("inf"), None, True):
        record[pred.feature_names[0]] = bad
        with assert_raises(PredictionInputError, "finite number"):
            pred.predict_record(record)


def test_rows_without_any_valid_values_are_reported_as_rejected():
    d = tempfile.mkdtemp()
    train_and_evaluate(small_dataset(), mode="multiclass", artifacts_dir=d)
    pred = Predictor.load(d)
    df = pd.DataFrame({f: [1.0, np.nan] for f in pred.feature_names})
    out = pred.predict_dataframe(df)
    assert len(out["results"]) == 1 and out["rejected"][0]["row_index"] == 1


def test_severity_policy():
    assert severity_for("Normal") == "None"
    assert severity_for("Suspicious") == "Medium"
    assert severity_for("DoS Hulk") == "High" and severity_for("DDoS") == "High"
    assert severity_for("PortScan") == "Medium" and severity_for("Brute Force") == "Medium"


def test_synthetic_generator_is_deterministic_and_has_expected_labels():
    a, b = generate_synthetic_flows(500, seed=2), generate_synthetic_flows(500, seed=2)
    pd.testing.assert_frame_equal(a, b)
    assert set(a["Label"]) == {"BENIGN", "DoS", "PortScan", "Brute Force"}
    assert a["Flow ID"].str.startswith("SYN-").all()
