"""Inference: load the saved bundle and classify flow records."""
from __future__ import annotations

import math
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ml.config import BUNDLE_FILENAME, DEFAULT_ARTIFACTS_DIR, NORMAL_LABEL
from ml.preprocessing import extract_features, map_columns
from ml.severity import severity_for

PROBABILITY_NOTE = ("Probability is the model's estimate for the predicted class. It is not a "
                    "calibrated risk score and does not confirm an intrusion.")


class ModelNotTrainedError(RuntimeError):
    """No saved model is available."""


class PredictionInputError(ValueError):
    """The supplied records do not match the model's input schema."""


class Predictor:
    def __init__(self, bundle: dict):
        self._b = bundle
        self.pipeline = bundle["pipeline"]
        self.feature_names: list[str] = bundle["feature_names"]

    @classmethod
    def load(cls, artifacts_dir=None) -> "Predictor":
        path = Path(artifacts_dir or DEFAULT_ARTIFACTS_DIR) / BUNDLE_FILENAME
        if not path.is_file():
            raise ModelNotTrainedError("No trained model found. Train a model first.")
        try:
            return cls(joblib.load(path))
        except Exception as exc:  # corrupt or incompatible file
            raise ModelNotTrainedError(f"The saved model could not be loaded: {exc}") from exc

    @property
    def metadata(self) -> dict:
        keys = ("model_id", "model_name", "mode", "dataset_name", "is_synthetic",
                "trained_at", "schema_version", "classes")
        return {**{k: self._b[k] for k in keys}, "feature_names": self.feature_names}

    def predict_dataframe(self, df: pd.DataFrame) -> dict:
        """Classify every usable row. Returns {'results': [...], 'rejected': [...]}."""
        mapping, _ = map_columns(df.columns)
        missing = [f for f in self.feature_names if f not in mapping]
        if missing:
            raise PredictionInputError("Missing required feature columns: " + ", ".join(missing))
        X = extract_features(df, mapping, self.feature_names)

        usable = X.notna().any(axis=1).to_numpy()
        rejected = [{"row_index": int(i), "reason": "No valid numeric feature values"}
                    for i in np.flatnonzero(~usable)]
        if not usable.any():
            return {"results": [], "rejected": rejected}

        Xu = X[usable]
        positions = np.flatnonzero(usable)
        classes = list(self.pipeline.classes_)
        has_proba = hasattr(self.pipeline, "predict_proba")
        proba = self.pipeline.predict_proba(Xu) if has_proba else None
        if proba is not None:
            labels = [classes[i] for i in proba.argmax(axis=1)]
        else:
            labels = list(self.pipeline.predict(Xu))
        imputed = Xu.isna().sum(axis=1).to_numpy()

        results = []
        for k, pos in enumerate(positions):
            label = str(labels[k])
            row = {
                "row_index": int(pos), "predicted_class": label,
                "is_suspicious": label != NORMAL_LABEL, "severity": severity_for(label),
                "confidence": None, "probabilities": None, "imputed_features": int(imputed[k]),
            }
            if proba is not None:
                p = proba[k]
                row["confidence"] = round(float(p.max()), 4)
                top = np.argsort(p)[::-1][:3]
                row["probabilities"] = {str(classes[i]): round(float(p[i]), 4) for i in top}
            results.append(row)
        return {"results": results, "rejected": rejected}

    def predict_record(self, record: dict) -> dict:
        """Classify one flow. Every model feature must be present and finite."""
        mapping, _ = map_columns(list(record.keys()))
        problems = []
        for f in self.feature_names:
            if f not in mapping:
                problems.append(f"{f}: missing")
                continue
            value = record[mapping[f]]
            try:
                ok = math.isfinite(float(value)) and not isinstance(value, bool)
            except (TypeError, ValueError):
                ok = False
            if not ok:
                problems.append(f"{f}: must be a finite number")
        if problems:
            raise PredictionInputError("Invalid record. " + "; ".join(problems))
        out = self.predict_dataframe(pd.DataFrame([record]))
        return out["results"][0]
