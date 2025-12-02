# src/env_check/anomaly_detector.py

import math
import re
from .drift_detection import load_env_file


def shannon_entropy(value: str) -> float:
    """Calculate Shannon entropy of a value (detect secrets/tokens)."""
    if not value:
        return 0.0
    freq = {c: value.count(c) for c in set(value)}
    entropy = -sum((count/len(value)) * math.log2(count/len(value)) for count in freq.values())
    return entropy


def infer_type(key: str, value: str):
    """Infer the expected type of the variable."""
    if "URL" in key or "URI" in key:
        return "url"
    if "EMAIL" in key:
        return "email"
    if key.startswith("IS_") or key.endswith("_ENABLED"):
        return "bool"
    if key.endswith("_ID") or key.endswith("_COUNT") or key.endswith("_LIMIT"):
        return "number"
    return "string"


def type_mismatch(expected_type, value):
    """Check if the value aligns with expected type."""
    if expected_type == "url":
        return not re.match(r"^https?://", value)
    if expected_type == "email":
        return not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value)
    if expected_type == "bool":
        return value.lower() not in ("true", "false", "1", "0")
    if expected_type == "number":
        return not value.isdigit()
    return False  # string has no mismatch


def detect_anomalies(env_file, other_env_files=None):
    env = load_env_file(env_file)
    anomalies = []

    # Load other env files for cross-env anomaly comparisons
    others = []
    if other_env_files:
        for f in other_env_files:
            if f != env_file:
                others.append(load_env_file(f))

    for key, value in env.items():

        # RULE 1: entropy detection
        entropy = shannon_entropy(value)
        if entropy > 4.0:  # high entropy → probably secret
            anomalies.append((key, value, "High entropy value (possible secret leakage)"))

        # RULE 2: length heuristics
        if len(value) <= 1:
            anomalies.append((key, value, "Suspiciously short value"))
        if len(value) >= 80:
            anomalies.append((key, value, "Suspiciously long value"))

        # RULE 3: type inference
        expected = infer_type(key, value)
        if type_mismatch(expected, value):
            anomalies.append((key, value, f"Value does not match inferred type '{expected}'"))

        # RULE 4: cross-file consistency
        for other in others:
            if key in other and other[key] != value:
                # Drastic value difference detection (entropy jump)
                if abs(shannon_entropy(other[key]) - entropy) > 1.5:
                    anomalies.append((key, value, "Value diverges significantly across environment files"))

    return anomalies
