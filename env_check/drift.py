import os
import json
import hashlib
from datetime import datetime
from difflib import unified_diff

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".cache")
DRIFT_DIR = os.path.join(CACHE_DIR, "drift")

def _ensure():
    os.makedirs(DRIFT_DIR, exist_ok=True)

def _hash_dict(d):
    s = json.dumps(d, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def save_snapshot(name, env_dict):
    """
    Save snapshot for env file 'name' (e.g. '.env', '.env.production')
    """
    _ensure()
    h = _hash_dict(env_dict)
    ts = datetime.utcnow().isoformat() + "Z"
    filename = f"{name.replace(os.sep,'_')}_{ts}.json"
    path = os.path.join(DRIFT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"ts": ts, "hash": h, "env": env_dict}, f, indent=2)
    return path

def latest_snapshots(name, count=2):
    files = sorted([f for f in os.listdir(DRIFT_DIR) if f.startswith(name.replace(os.sep,'_'))])
    if not files:
        return []
    return [os.path.join(DRIFT_DIR, f) for f in files[-count:]]

def compare_snapshots(name):
    paths = latest_snapshots(name, 2)
    if len(paths) < 2:
        return {"status": "no_history", "details": "Not enough snapshots to compare."}

    with open(paths[0], "r", encoding="utf-8") as f:
        a = json.load(f)["env"]
    with open(paths[1], "r", encoding="utf-8") as f:
        b = json.load(f)["env"]

    added = [k for k in b.keys() if k not in a]
    removed = [k for k in a.keys() if k not in b]
    changed = [k for k in b.keys() if k in a and a[k] != b[k]]

    diff_text = "\n".join(list(unified_diff(
        json.dumps(a, indent=2).splitlines(),
        json.dumps(b, indent=2).splitlines(),
        fromfile="previous",
        tofile="current",
        lineterm=""
    )))

    return {"status": "ok", "added": added, "removed": removed, "changed": changed, "diff": diff_text, "paths": paths}


def compare_env_dicts(a, b):
    """
    Compare two env dicts.
    Auto-normalize non-dict inputs into empty dicts.
    """
    if not isinstance(a, dict):
        a = {}
    if not isinstance(b, dict):
        b = {}

    added = [k for k in b.keys() if k not in a]
    removed = [k for k in a.keys() if k not in b]
    changed = {k: (a[k], b[k]) for k in a.keys() & b.keys() if a[k] != b[k]}

    return {
        "missing_in_file1": removed,
        "missing_in_file2": added,
        "different_values": changed,
    }


def drift_compare(file1, file2):
    from .drift_detection import compare_env_files, format_drift_report
    result = compare_env_files(file1, file2)
    print(format_drift_report(result, file1, file2))

