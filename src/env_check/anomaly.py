# src/env_check/anomaly.py
import json
import os
import statistics
from .secret_analyzer import SecretAnalyzer

CACHE_DIR = ".cache"
ANOMALY_BASELINE = os.path.join(CACHE_DIR, "anomaly_baseline.json")

class SimpleAnomalyDetector:
    def __init__(self, env_vars: dict):
        self.env = env_vars
        os.makedirs(CACHE_DIR, exist_ok=True)

    def _make_features(self, key, value):
        # features used for anomaly detection
        token_type = SecretAnalyzer.detect_token_type(value)
        entropy = SecretAnalyzer.calculate_entropy(value)
        length = len(value or "")
        # numeric-ish check
        digits_fraction = sum(c.isdigit() for c in (value or "")) / max(1, length)
        return {
            "key": key,
            "token_type": token_type,
            "entropy": entropy,
            "length": length,
            "digits_fraction": digits_fraction
        }

    def analyze(self, persist_baseline_if_missing=True):
        """
        Returns (issues, info_messages)
        issues: list of anomaly flags
        info_messages: list of info strings (e.g., baseline created)
        """
        features = {}
        for k, v in self.env.items():
            features[k] = self._make_features(k, v)

        # load baseline if exists
        if os.path.exists(ANOMALY_BASELINE):
            with open(ANOMALY_BASELINE, "r", encoding="utf-8") as f:
                baseline = json.load(f)
        else:
            baseline = None

        if baseline is None:
            if persist_baseline_if_missing:
                # persist current features as baseline
                with open(ANOMALY_BASELINE, "w", encoding="utf-8") as f:
                    json.dump(features, f, indent=2)
                return [], ["Anomaly baseline created. No anomaly flags this run."]
            else:
                return [], ["No baseline found and persist disabled."]

        # compare per-key features simple heuristics
        issues = []
        info = []
        for k, feat in features.items():
            if k not in baseline:
                info.append(f"Key '{k}' not in baseline (new key).")
                continue
            b = baseline[k]
            # check entropy drop or increase beyond reasonable delta
            try:
                be = float(b.get("entropy", 0.0))
                if abs(feat["entropy"] - be) > 2.0:
                    issues.append({
                        "type": "anomaly_entropy",
                        "key": k,
                        "message": f"Entropy for {k} changed from {be:.2f} -> {feat['entropy']:.2f}"
                    })
            except Exception:
                pass
            # length change
            try:
                bl = int(b.get("length", 0))
                if bl > 0 and abs(feat["length"] - bl) / bl > 0.5:
                    issues.append({
                        "type": "anomaly_length",
                        "key": k,
                        "message": f"Length for {k} changed from {bl} -> {feat['length']}"
                    })
            except Exception:
                pass

        return issues, info
