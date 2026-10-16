"""Metrics computed from real predictions. Nothing here is estimated or invented."""
from __future__ import annotations

import numpy as np
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support

from ml.config import NORMAL_LABEL, SUSPICIOUS_LABEL


def compute_metrics(y_true, y_pred, labels: list[str], mode: str) -> dict:
    labels = list(labels)
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    prec, rec, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, zero_division=0)
    total = int(cm.sum())

    per_class = []
    for i, label in enumerate(labels):
        tp = int(cm[i, i])
        fp = int(cm[:, i].sum() - tp)
        fn = int(cm[i, :].sum() - tp)
        tn = total - tp - fp - fn
        fpr = fp / (fp + tn) if (fp + tn) > 0 else None
        per_class.append({
            "class": label, "precision": float(prec[i]), "recall": float(rec[i]),
            "f1": float(f1[i]), "support": int(support[i]),
            "false_positive_rate": None if fpr is None else float(fpr),
        })

    weights = support / support.sum() if support.sum() else support
    weighted = {
        "precision": float((prec * weights).sum()),
        "recall": float((rec * weights).sum()),
        "f1": float((f1 * weights).sum()),
    }
    macro = {"precision": float(prec.mean()), "recall": float(rec.mean()), "f1": float(f1.mean())}

    if mode == "binary":
        pos = labels.index(SUSPICIOUS_LABEL)
        headline = {"precision": float(prec[pos]), "recall": float(rec[pos]), "f1": float(f1[pos])}
        averaging = f"binary (positive class: {SUSPICIOUS_LABEL})"
    else:
        headline = macro
        averaging = "macro (unweighted mean over classes)"

    normal_flagged_rate = None
    if NORMAL_LABEL in labels:
        i = labels.index(NORMAL_LABEL)
        n_normal = int(cm[i, :].sum())
        if n_normal > 0:
            normal_flagged_rate = float((n_normal - cm[i, i]) / n_normal)

    return {
        "accuracy": float(np.trace(cm) / total) if total else 0.0,
        "headline": headline,
        "averaging": averaging,
        "macro": macro,
        "weighted": weighted,
        "normal_flagged_rate": normal_flagged_rate,
        "confusion_matrix": {"labels": labels, "matrix": cm.tolist()},
        "per_class": per_class,
        "test_samples": total,
    }
