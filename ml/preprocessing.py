"""Dataset loading, validation, feature mapping and cleaning.

Nothing here fits a model or learns statistics from data, so it cannot leak
information between training and test sets. Learned steps (imputation, scaling)
live inside the scikit-learn pipelines built in train.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from ml.config import (MAX_FILE_BYTES, MAX_ROWS, MIN_MAPPED_FEATURES, NORMAL_LABEL,
                       SUSPICIOUS_LABEL)
from ml.feature_schema import (ALIAS_INDEX, EXCLUDED_COLUMNS, FEATURE_NAMES,
                               LABEL_CANDIDATES, NORMAL_LABELS, normalize_name)


class DatasetError(ValueError):
    """Raised when a dataset cannot be loaded, validated or used."""


# --------------------------------------------------------------------------- loading
def load_csv(path, max_rows: int = MAX_ROWS, max_bytes: int = MAX_FILE_BYTES) -> pd.DataFrame:
    """Load a CSV as plain data. Never evaluates or executes file contents."""
    path = Path(path)
    if not path.is_file():
        raise DatasetError(f"File not found: {path.name}")
    if path.suffix.lower() != ".csv":
        raise DatasetError("Only .csv files are supported.")
    size = path.stat().st_size
    if size == 0:
        raise DatasetError("The file is empty.")
    if size > max_bytes:
        raise DatasetError(f"File is {size / 1e6:.0f} MB; the limit is {max_bytes / 1e6:.0f} MB.")
    try:
        df = pd.read_csv(path, nrows=max_rows + 1, skipinitialspace=True,
                         low_memory=False, encoding_errors="replace")
    except (pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise DatasetError(f"The file could not be parsed as CSV: {exc}") from exc
    if len(df) > max_rows:
        raise DatasetError(f"File has more than {max_rows:,} rows.")
    if df.empty:
        raise DatasetError("The file contains a header but no data rows.")
    df.columns = [str(c).strip() for c in df.columns]
    return df


# --------------------------------------------------------------------------- mapping
def detect_label_column(columns) -> str | None:
    by_norm = {normalize_name(c): c for c in columns}
    for candidate in LABEL_CANDIDATES:
        if candidate in by_norm:
            return by_norm[candidate]
    return None


def map_columns(columns) -> tuple[dict[str, str], list[dict[str, str]]]:
    """Return ({canonical_feature: original_column}, unsupported_columns)."""
    mapping: dict[str, str] = {}
    unsupported: list[dict[str, str]] = []
    for col in columns:
        norm = normalize_name(col)
        canonical = ALIAS_INDEX.get(norm)
        if canonical and canonical not in mapping:
            mapping[canonical] = col
        else:
            reason = EXCLUDED_COLUMNS.get(norm, "Not part of the supported feature schema")
            if canonical:
                reason = f"Duplicate of already-mapped feature '{canonical}'"
            unsupported.append({"column": col, "reason": reason})
    return mapping, unsupported


def extract_features(df: pd.DataFrame, mapping: dict[str, str], feature_names) -> pd.DataFrame:
    """Numeric feature matrix with canonical column names. Inf becomes NaN."""
    out = pd.DataFrame(index=df.index)
    for name in feature_names:
        out[name] = pd.to_numeric(df[mapping[name]], errors="coerce")
    return out.replace([np.inf, -np.inf], np.nan)


# --------------------------------------------------------------------------- labels
def normalize_labels(series: pd.Series) -> pd.Series:
    """Tidy label text and map benign synonyms to the canonical 'Normal'."""
    s = series.astype("string").str.strip()
    s = s.str.replace("\ufffd", "-", regex=False).str.replace(r"\s+", " ", regex=True)
    s = s.mask(s == "", pd.NA)
    is_normal = s.str.lower().isin(NORMAL_LABELS).fillna(False)
    return s.mask(is_normal, NORMAL_LABEL)


def to_binary(y: pd.Series) -> pd.Series:
    return y.map(lambda v: NORMAL_LABEL if v == NORMAL_LABEL else SUSPICIOUS_LABEL)


# --------------------------------------------------------------------------- validation
@dataclass
class ValidationReport:
    rows: int
    columns: int
    label_column: str | None
    mapped_features: dict[str, str]
    missing_features: list[str]
    unsupported_columns: list[dict[str, str]]
    missing_values: dict[str, int]
    infinite_values: dict[str, int]
    non_numeric_values: dict[str, int]
    duplicate_rows: int
    missing_labels: int
    class_distribution: dict[str, int]
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["is_valid"] = self.is_valid
        return d


def validate_dataframe(df: pd.DataFrame, label_column: str | None = None,
                       require_label: bool = True) -> ValidationReport:
    errors: list[str] = []
    warnings: list[str] = []

    detected = label_column
    if label_column is not None and label_column not in df.columns:
        errors.append(f"Label column '{label_column}' was not found in the file.")
        detected = None
    elif label_column is None:
        detected = detect_label_column(df.columns)
        if detected is None and require_label:
            errors.append("No label column detected. Select the column that holds the "
                          "traffic class (for example 'Label').")

    mapping, unsupported = map_columns([c for c in df.columns if c != detected])
    missing_features = [f for f in FEATURE_NAMES if f not in mapping]
    if len(mapping) < MIN_MAPPED_FEATURES:
        errors.append(f"Only {len(mapping)} schema features were found; at least "
                      f"{MIN_MAPPED_FEATURES} are required. Missing: {', '.join(missing_features)}.")
    elif missing_features:
        warnings.append(f"{len(missing_features)} schema features are absent and will not be "
                        f"used: {', '.join(missing_features)}.")

    missing_values, infinite_values, non_numeric = {}, {}, {}
    for name, col in mapping.items():
        raw = df[col]
        num = pd.to_numeric(raw, errors="coerce")
        inf = int(np.isinf(num).sum())
        bad = int((num.isna() & raw.notna()).sum())
        miss = int(raw.isna().sum())
        if miss:
            missing_values[name] = miss
        if inf:
            infinite_values[name] = inf
        if bad:
            non_numeric[name] = bad
    if non_numeric:
        warnings.append(f"Non-numeric entries in {len(non_numeric)} feature column(s) were treated as missing.")

    dup_cols = list(mapping.values()) + ([detected] if detected else [])
    duplicate_rows = int(df.duplicated(subset=dup_cols).sum()) if dup_cols else 0
    if duplicate_rows:
        warnings.append(f"{duplicate_rows:,} duplicate rows will be removed before training.")

    class_distribution: dict[str, int] = {}
    missing_labels = 0
    if detected:
        labels = normalize_labels(df[detected])
        missing_labels = int(labels.isna().sum())
        class_distribution = {str(k): int(v) for k, v in labels.value_counts().items()}
        if missing_labels:
            warnings.append(f"{missing_labels:,} rows have no label and will be removed.")
        if class_distribution:
            smallest = min(class_distribution.values())
            if smallest < 0.05 * sum(class_distribution.values()):
                warnings.append("Classes are imbalanced; accuracy alone can be misleading. "
                                "Review recall and false positive rate.")

    return ValidationReport(
        rows=len(df), columns=len(df.columns), label_column=detected,
        mapped_features=mapping, missing_features=missing_features,
        unsupported_columns=unsupported, missing_values=missing_values,
        infinite_values=infinite_values, non_numeric_values=non_numeric,
        duplicate_rows=duplicate_rows, missing_labels=missing_labels,
        class_distribution=class_distribution, errors=errors, warnings=warnings)


# --------------------------------------------------------------------------- cleaning
@dataclass
class CleanedData:
    X: pd.DataFrame
    y: pd.Series
    stats: dict


def clean_dataset(df: pd.DataFrame, mapping: dict[str, str], label_column: str) -> CleanedData:
    """Remove unusable rows. Remaining NaNs are imputed later, inside the pipeline."""
    rows_before = len(df)
    feature_names = [f for f in FEATURE_NAMES if f in mapping]
    X = extract_features(df, mapping, feature_names)
    labels = normalize_labels(df[label_column])

    inf_replaced = int(sum(np.isinf(pd.to_numeric(df[mapping[f]], errors="coerce")).sum()
                           for f in feature_names))

    has_label = labels.notna()
    dropped_missing_label = int((~has_label).sum())
    X, labels = X[has_label], labels[has_label]

    usable = X.notna().any(axis=1)
    dropped_no_features = int((~usable).sum())
    X, labels = X[usable], labels[usable]

    y = labels.astype(object)
    dup = pd.concat([X, y.rename("__label__")], axis=1).duplicated(keep="first")
    dropped_duplicates = int(dup.sum())
    X, y = X[~dup], y[~dup]

    stats = {
        "rows_before": rows_before,
        "rows_after": len(X),
        "dropped_missing_label": dropped_missing_label,
        "dropped_no_valid_features": dropped_no_features,
        "dropped_duplicates": dropped_duplicates,
        "infinite_values_replaced": inf_replaced,
        "missing_cells_to_impute": int(X.isna().sum().sum()),
        "features_used": feature_names,
    }
    return CleanedData(X=X, y=y, stats=stats)
