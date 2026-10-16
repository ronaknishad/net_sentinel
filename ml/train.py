"""Model training and comparison.

All learned preprocessing (imputation, scaling) sits inside each scikit-learn
Pipeline and is fitted on the training split only.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler
from sklearn.tree import DecisionTreeClassifier

from ml.config import (BUNDLE_FILENAME, DEFAULT_ARTIFACTS_DIR, DEFAULT_TEST_SIZE,
                       EVALUATION_FILENAME, MIN_CLASS_SAMPLES, NORMAL_LABEL, RANDOM_SEED,
                       SUSPICIOUS_LABEL)
from ml.evaluate import compute_metrics
from ml.feature_schema import SCHEMA_VERSION
from ml.preprocessing import (DatasetError, clean_dataset, load_csv, to_binary,
                              validate_dataframe)
from ml.transformers import signed_log1p

MODEL_NAMES = ("Random Forest", "Decision Tree", "Logistic Regression")


def build_pipeline(name: str, seed: int = RANDOM_SEED) -> Pipeline:
    imputer = ("imputer", SimpleImputer(strategy="median", keep_empty_features=True))
    if name == "Random Forest":
        clf = RandomForestClassifier(n_estimators=150, class_weight="balanced_subsample",
                                     n_jobs=-1, random_state=seed)
        return Pipeline([imputer, ("classifier", clf)])
    if name == "Decision Tree":
        clf = DecisionTreeClassifier(max_depth=12, class_weight="balanced", random_state=seed)
        return Pipeline([imputer, ("classifier", clf)])
    if name == "Logistic Regression":
        clf = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=seed)
        return Pipeline([imputer, ("signed_log", FunctionTransformer(signed_log1p)),
                         ("scaler", StandardScaler()), ("classifier", clf)])
    raise ValueError(f"Unknown model: {name}")


def split_data(y: pd.Series, test_size: float = DEFAULT_TEST_SIZE, seed: int = RANDOM_SEED):
    """Stratified, seeded split. Returns disjoint positional index arrays."""
    return train_test_split(np.arange(len(y)), test_size=test_size, stratify=y, random_state=seed)


def _class_counts(y) -> dict[str, int]:
    return {str(k): int(v) for k, v in pd.Series(y).value_counts().items()}


def train_and_evaluate(df: pd.DataFrame, label_column: str | None = None,
                       mode: str = "multiclass", test_size: float = DEFAULT_TEST_SIZE,
                       seed: int = RANDOM_SEED, dataset_name: str = "dataset",
                       is_synthetic: bool = False, artifacts_dir=None, save: bool = True,
                       min_class_samples: int = MIN_CLASS_SAMPLES) -> dict:
    if mode not in ("binary", "multiclass"):
        raise ValueError("mode must be 'binary' or 'multiclass'")
    artifacts_dir = Path(artifacts_dir or DEFAULT_ARTIFACTS_DIR)

    report = validate_dataframe(df, label_column)
    if not report.is_valid:
        raise DatasetError("Dataset validation failed: " + " ".join(report.errors))
    cleaned = clean_dataset(df, report.mapped_features, report.label_column)
    X, y = cleaned.X, cleaned.y
    if mode == "binary":
        y = to_binary(y)

    counts = y.value_counts()
    dropped_classes = {str(c): int(n) for c, n in counts.items() if n < min_class_samples}
    keep = ~y.isin(list(dropped_classes))
    X, y = X[keep], y[keep]
    classes = sorted(y.unique(), key=lambda c: (c != NORMAL_LABEL, c))
    if len(classes) < 2:
        raise DatasetError("At least two classes with enough samples are required to train a classifier.")
    if mode == "binary" and set(classes) != {NORMAL_LABEL, SUSPICIOUS_LABEL}:
        raise DatasetError("Binary mode needs both Normal and non-Normal traffic in the dataset.")

    train_idx, test_idx = split_data(y, test_size, seed)
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    models, comparison, fitted = {}, [], {}
    for name in MODEL_NAMES:
        pipe = build_pipeline(name, seed)
        t0 = time.perf_counter()
        pipe.fit(X_train, y_train)
        seconds = time.perf_counter() - t0
        metrics = compute_metrics(y_test, pipe.predict(X_test), classes, mode)
        metrics["training_seconds"] = round(seconds, 3)
        models[name], fitted[name] = metrics, pipe
        comparison.append({
            "model": name, "accuracy": metrics["accuracy"], **metrics["headline"],
            "normal_flagged_rate": metrics["normal_flagged_rate"],
            "training_seconds": metrics["training_seconds"],
        })

    selected = max(comparison, key=lambda r: (r["f1"], r["recall"]))["model"]
    trained_at = datetime.now(timezone.utc)
    model_id = f"{selected.lower().replace(' ', '-')}-{trained_at:%Y%m%d%H%M%S}"

    importances = None
    clf = fitted[selected].named_steps["classifier"]
    if hasattr(clf, "feature_importances_"):
        pairs = sorted(zip(cleaned.stats["features_used"], clf.feature_importances_),
                       key=lambda p: -p[1])
        importances = [{"feature": f, "importance": float(v)} for f, v in pairs]

    evaluation = {
        "model_id": model_id, "selected_model": selected, "mode": mode,
        "dataset_name": dataset_name, "is_synthetic": is_synthetic,
        "provenance_note": ("Synthetic demonstration data. These scores describe the generator's rules, "
                            "not real-world detection performance." if is_synthetic else
                            "Scores come from the held-out test split of the supplied dataset."),
        "trained_at": trained_at.isoformat(), "random_seed": seed,
        "split": {"test_size": test_size, "stratified": True,
                  "train_samples": int(len(train_idx)), "test_samples": int(len(test_idx)),
                  "train_class_distribution": _class_counts(y_train),
                  "test_class_distribution": _class_counts(y_test)},
        "class_distribution": _class_counts(y),
        "classes": classes, "dropped_classes": dropped_classes,
        "preprocessing": cleaned.stats,
        "validation_warnings": report.warnings,
        "unsupported_columns": report.unsupported_columns,
        "models": models, "model_comparison": comparison,
        "feature_importances": importances,
        "probability_note": ("Predicted class probabilities are model estimates. They are not "
                             "calibrated risk scores and do not confirm an intrusion."),
    }

    if save:
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        bundle = {
            "pipeline": fitted[selected], "feature_names": cleaned.stats["features_used"],
            "classes": classes, "mode": mode, "model_id": model_id, "model_name": selected,
            "trained_at": evaluation["trained_at"], "dataset_name": dataset_name,
            "is_synthetic": is_synthetic, "schema_version": SCHEMA_VERSION,
        }
        _atomic_write(artifacts_dir / BUNDLE_FILENAME, lambda p: joblib.dump(bundle, p))
        _atomic_write(artifacts_dir / EVALUATION_FILENAME,
                      lambda p: Path(p).write_text(json.dumps(evaluation, indent=2), encoding="utf-8"))
    return evaluation


def _atomic_write(target: Path, writer) -> None:
    tmp = target.with_suffix(target.suffix + ".tmp")
    writer(tmp)
    os.replace(tmp, target)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and evaluate NetSentinel classifiers.")
    parser.add_argument("--csv", required=True, help="Path to a labelled flow CSV")
    parser.add_argument("--mode", choices=("binary", "multiclass"), default="multiclass")
    parser.add_argument("--label-column", default=None)
    parser.add_argument("--synthetic", action="store_true", help="Mark the data as synthetic")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    parser.add_argument("--test-size", type=float, default=DEFAULT_TEST_SIZE)
    parser.add_argument("--yes", action="store_true", help="Confirm training on a file over 100 MB")
    args = parser.parse_args()

    path = Path(args.csv)
    if path.is_file() and path.stat().st_size > 100 * 1024 * 1024 and not args.yes:
        raise SystemExit(f"{path.name} is {path.stat().st_size / 1e6:.0f} MB. Training may be slow "
                         "and memory-hungry. Re-run with --yes to confirm.")
    ev = train_and_evaluate(load_csv(path), args.label_column, args.mode, args.test_size, args.seed,
                            dataset_name=path.name, is_synthetic=args.synthetic)
    print(f"\nDataset: {ev['dataset_name']}  |  mode: {ev['mode']}  |  synthetic: {ev['is_synthetic']}")
    pre = ev["preprocessing"]
    print(f"Rows: {pre['rows_before']:,} -> {pre['rows_after']:,} after cleaning "
          f"(duplicates removed: {pre['dropped_duplicates']}, infinite values replaced: {pre['infinite_values_replaced']})")
    print(f"Train/test: {ev['split']['train_samples']:,} / {ev['split']['test_samples']:,}\n")
    print(f"{'Model':<22}{'Acc':>8}{'Prec':>8}{'Rec':>8}{'F1':>8}{'Normal flagged':>16}{'Secs':>8}")
    for r in ev["model_comparison"]:
        nf = "n/a" if r["normal_flagged_rate"] is None else f"{r['normal_flagged_rate']:.4f}"
        print(f"{r['model']:<22}{r['accuracy']:>8.4f}{r['precision']:>8.4f}{r['recall']:>8.4f}"
              f"{r['f1']:>8.4f}{nf:>16}{r['training_seconds']:>8.2f}")
    print(f"\nSelected: {ev['selected_model']} (saved as {ev['model_id']})")
    if ev["is_synthetic"]:
        print("NOTE: synthetic data. Scores are not real-world benchmarks.")


if __name__ == "__main__":
    main()
