"""Picklable helpers used inside scikit-learn pipelines."""
import numpy as np


def signed_log1p(x):
    """Compress heavy-tailed values (bytes/s, durations) while keeping the sign."""
    x = np.asarray(x, dtype=float)
    return np.sign(x) * np.log1p(np.abs(x))
