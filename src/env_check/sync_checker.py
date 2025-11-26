def load_env_keyset(path):
    keys = set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k = line.split("=", 1)[0].strip()
                keys.add(k)
    except FileNotFoundError:
        pass
    return keys

def compare_envs(paths):
    """
    paths: list of file paths
    returns list of issues describing missing/out-of-sync keys
    """
    sets = {p: load_env_keyset(p) for p in paths}
    issues = []
    # union of keys
    all_keys = set().union(*sets.values()) if sets else set()
    for key in sorted(all_keys):
        present_in = [p for p, s in sets.items() if key in s]
        missing_in = [p for p in sets.keys() if p not in present_in]
        if missing_in:
            issues.append({
                "type": "sync_missing",
                "severity": "warning",
                "key": key,
                "present_in": present_in,
                "missing_in": missing_in,
                "message": f"Key '{key}' present in {present_in} but missing in {missing_in}"
            })
    return issues
