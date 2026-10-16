"""Documented severity policy for predicted classes.

Severity comes from the predicted label only. It is NOT derived from the model
probability, and it does not mean the activity was independently verified.
"""
from __future__ import annotations

from ml.config import NORMAL_LABEL, SUSPICIOUS_LABEL

HIGH_KEYWORDS = ("dos", "ddos", "bot", "infiltration", "heartbleed", "sql injection")

SEVERITY_POLICY = [
    {"severity": "High", "rule": "Predicted label contains: " + ", ".join(HIGH_KEYWORDS)},
    {"severity": "Medium", "rule": "Any other predicted attack label, including the binary label 'Suspicious'"},
    {"severity": "None", "rule": "Predicted label is 'Normal'"},
]


def severity_for(label: str) -> str:
    if label == NORMAL_LABEL:
        return "None"
    if label == SUSPICIOUS_LABEL:
        return "Medium"
    lowered = label.lower()
    if any(k in lowered for k in HIGH_KEYWORDS):
        return "High"
    return "Medium"
